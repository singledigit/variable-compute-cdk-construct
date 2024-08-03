from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_certificatemanager as acm,
    aws_elasticloadbalancingv2 as elbv2,
    aws_elasticloadbalancingv2_targets as elbv2_targets,
    Environment
)
from constructs import Construct
from variable_compute.variable_compute import VariableCompute
from aws_cdk import aws_lambda as lambda_

class HybridConstructStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        env = Environment(account="088483494489", region="us-west-2")
        super().__init__(scope, construct_id, env=env, **kwargs)
        
        vpc = ec2.Vpc(
            self, "VPC",
            max_azs=2
        )

        cluster = ecs.Cluster(
            self, "Cluster",
            vpc=vpc
        )
        
        hosted_zone = route53.HostedZone.from_lookup(
            self, "HostedZone",
            domain_name="slip.link"
        )

        certificate = acm.Certificate.from_certificate_arn(
            self, "Certificate",
            certificate_arn="arn:aws:acm:us-west-2:088483494489:certificate/06e43f8a-3e6a-4bdf-adb3-7fc17100ee21"
        )
        
        alb = elbv2.ApplicationLoadBalancer(self, "HybridAlb",
            vpc=vpc,
            internet_facing=True,
            load_balancer_name="HybridAlb"
        )
        
         # Create Route 53 Alias Record
        route53.ARecord(self, "AliasRecord",
            zone=hosted_zone,
            target=route53.RecordTarget.from_alias(targets.LoadBalancerTarget(alb)),
            record_name="hybrid.slip.link"
        )
        
        var_compute = VariableCompute(
            self, "VariableCompute",
            code_location="src/func",
            handler="handler.handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            alb=alb,
            certificate=certificate,
            vpc=vpc
        )