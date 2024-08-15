from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_certificatemanager as acm,
    aws_elasticloadbalancingv2 as elbv2,
    CfnOutput as output,
    Environment
)
from constructs import Construct
from variable_compute.variable_compute import VariableCompute
from aws_cdk import aws_lambda as lambda_

class HybridConstructStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        env = Environment(account="088483494489", region="us-west-2")
        super().__init__(scope, construct_id, env=env, **kwargs)
        
        
        # VPC for fargate
        vpc = ec2.Vpc(
            self, "VPC",
            max_azs=2
        )

        # Cluster for Fargate
        cluster = ecs.Cluster(
            self, "Cluster",
            vpc=vpc
        )
        
        # Zone for custom domain
        hosted_zone = route53.HostedZone.from_lookup(
            self, "HostedZone",
            domain_name="slip.link"
        )

        # certificate for custom domain
        certificate = acm.Certificate.from_certificate_arn(
            self, "Certificate",
            certificate_arn="arn:aws:acm:us-west-2:088483494489:certificate/06e43f8a-3e6a-4bdf-adb3-7fc17100ee21"
        )
        
        # ALB for routing
        alb = elbv2.ApplicationLoadBalancer(self, "HybridAlb",
            vpc=vpc,
            internet_facing=True,
            load_balancer_name="HybridAlb"
        )
        
        route53.ARecord(self, "AliasRecord",
            zone=hosted_zone,
            target=route53.RecordTarget.from_alias(targets.LoadBalancerTarget(alb)),
            record_name="hybrid.slip.link"
        )
        
        # Default listener
        listener = alb.add_listener("HttpsListener",
            port=443,
            certificates=[certificate],
            default_action=elbv2.ListenerAction.fixed_response(
                status_code=404,
                content_type="text/plain",
                message_body="Page not found"
            )
        )
        
        
        # Variable compute constructs
        compute_configs = [
            {
                "id": "VariableCompute1",
                "code_location": "src/func1",
                "url_path": "/route1",
                "runtime": lambda_.Runtime.PYTHON_3_12,
                "desired_task_count": 2
            },
            {
                "id": "VariableCompute2",
                "code_location": "src/func2",
                "url_path": "/route2",
                "runtime": lambda_.Runtime.PYTHON_3_9,
                "desired_task_count": 2
            }
        ]

        for index, config in enumerate(compute_configs, start=1):  # start=1 to begin from 1
            VariableCompute(
                self, config["id"],
                code_location=config["code_location"],
                handler="handler.handler",
                runtime=config["runtime"],
                url_path=config["url_path"],
                listener=listener,
                priority=index,  # Use the loop index as the priority
                vpc=vpc,
                cluster=cluster,
                desired_task_count=config["desired_task_count"]
            )
