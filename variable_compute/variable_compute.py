from aws_cdk import (
    aws_lambda as lambda_,
    aws_elasticloadbalancingv2 as elbv2,
    aws_elasticloadbalancingv2_targets as elbv2_targets,
    aws_ec2 as ec2,
    BundlingOptions,
)
from constructs import Construct

class VariableCompute(Construct):
    
    ## Create the Lambda function
    def __init__(self, scope: Construct, id: str,
                 code_location: str,
                 handler: str,
                 runtime: lambda_.Runtime,
                 vpc: ec2.Vpc,
                 alb: elbv2.ApplicationLoadBalancer,
                 certificate: elbv2.ListenerCertificate,
                 **kwargs
                 ):
        super().__init__(scope, id, **kwargs)
        
        lambda_function = lambda_.Function(
            self, "LambdaFunction",
            code=lambda_.Code.from_asset(
                code_location,
                bundling=BundlingOptions(
                    image=runtime.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"
                    ]
                )
            ),
            handler=handler,
            runtime=runtime
        )
        
        # Create target group
        lambda_target_group = elbv2.ApplicationTargetGroup(self, "LambdaTargetGroup",
            vpc=vpc,
            targets=[elbv2_targets.LambdaTarget(lambda_function)]
        )
        
        weighted_lambda_target_group = elbv2.WeightedTargetGroup(
            weight=1,
            target_group=lambda_target_group
        )
        
        # Create HTTPS Listener with Lambda default
        listener = alb.add_listener("HttpsListener",
            port=443,
            certificates=[certificate],
            default_action=elbv2.ListenerAction.weighted_forward(
                target_groups=[
                    weighted_lambda_target_group
                ]
            )
        )