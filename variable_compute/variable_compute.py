from aws_cdk import (
    Duration,
    aws_lambda as lambda_,
    aws_elasticloadbalancingv2 as elbv2,
    aws_elasticloadbalancingv2_targets as elbv2_targets,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr_assets as ecr_assets,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_iam as iam,
    BundlingOptions
)
from constructs import Construct

class VariableCompute(Construct):
    
    #####################################
    ### Lambda setup ####################
    #####################################
    
    def __init__(self, scope: Construct, id: str,
                 code_location: str,
                 handler: str,
                 runtime: lambda_.Runtime,
                 url_path: str,
                 vpc: ec2.Vpc,
                 listener: elbv2.ApplicationListener,
                 priority: int,
                 cluster: ecs.Cluster,
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
        
        lambda_target_group = elbv2.ApplicationTargetGroup(self, "LambdaTargetGroup",
            vpc=vpc,
            targets=[elbv2_targets.LambdaTarget(lambda_function)]
        )
        
        weighted_lambda_target_group = elbv2.WeightedTargetGroup(
            weight=1,
            target_group=lambda_target_group
        )
        
        #####################################
        ### Fargate setup ###################
        #####################################
        
        docker_image_asset = ecr_assets.DockerImageAsset(
            self, "DockerImageAsset",
            directory="./",
            file="variable_compute/wrapper/Dockerfile",
            build_args={"FUNCTION_LOCATION": code_location}
        )
        
        task_definition = ecs.FargateTaskDefinition(
            self, "TaskDefinition",
            cpu=256,
            memory_limit_mib=512,
            family="hybrid-service",
            runtime_platform=ecs.RuntimePlatform(
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
                cpu_architecture=ecs.CpuArchitecture.ARM64
            )
        )
        
        task_definition.add_container(
            id="Container",
            image=ecs.ContainerImage.from_docker_image_asset(docker_image_asset),
            port_mappings=[ecs.PortMapping(container_port=3000)],
            environment={
                "FARGATE": "true"
            }
        )
        
        fargate_service = ecs.FargateService(
            self, "FargateService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=0,
        )
        
        fargate_target_group = elbv2.ApplicationTargetGroup(
            self, "FargateTargetGroup",
            vpc=vpc,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[fargate_service]
        )
        
        weighted_fargate_target_group = elbv2.WeightedTargetGroup(
            weight=0,
            target_group=fargate_target_group
        )

        # listener = alb.add_listener("HttpsListener",
        #     port=443,
        #     certificates=[certificate],
        #     default_action=elbv2.ListenerAction.weighted_forward(
        #         target_groups=[
        #             weighted_lambda_target_group,
        #             weighted_fargate_target_group
        #         ]
        #     )
        # )
        
        # Adds condition for the path
        route_rule = elbv2.ApplicationListenerRule(self, "PathRule",
            listener=listener,
            priority=priority,
            conditions=[elbv2.ListenerCondition.path_patterns([url_path])],
            action=elbv2.ListenerAction.weighted_forward(
                target_groups=[
                    weighted_lambda_target_group,
                    weighted_fargate_target_group
                ]
            )
        )
        
        route_rule.node.add_dependency(lambda_target_group)
        route_rule.node.add_dependency(fargate_target_group)
        
        ## State Machine
        state_machine_role = iam.Role(self, "StateMachineRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaRole")
            ]
        )
        
        state_machine_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "elasticloadbalancing:ModifyRule",
                "elasticloadbalancing:ModifyListener",
                "elasticloadbalancing:DescribeRules",
                "elasticloadbalancing:DescribeListeners",
                "elasticloadbalancing:DescribeTargetGroups",
                "elasticloadbalancing:DescribeTargetHealth",
                "ecs:UpdateService",
                "ecs:DescribeServices"
            ],
            resources=["*"]
        ))

        # Define tasks for state machine
        hydrate_ecs_task = tasks.CallAwsService(self, "Hydrate ECS running task count",
            service="ecs",
            action="updateService",
            parameters={
                "Cluster": cluster.cluster_name,
                "Service": fargate_service.service_name,
                "DesiredCount": 3
            },
            iam_resources=["*"],
            result_path="$.result"
        )

        get_task_count_task = tasks.CallAwsService(self, "Get task count",
            service="ecs",
            action="describeServices",
            parameters={
                "Cluster": cluster.cluster_name,
                "Services": [fargate_service.service_name]
            },
            iam_resources=["*"],
            result_path="$.result"
        )

        is_fargate_active_choice = sfn.Choice(self, "Is Fargate active?")
        is_fargate_active_choice.when(sfn.Condition.number_greater_than_equals("$.result.Services[0].RunningCount", 3), 
                                      tasks.CallAwsService(self, "Fargate",
                                        service="elasticloadbalancingv2",
                                        action="modifyRule",
                                        parameters={
                                            "RuleArn": route_rule.listener_rule_arn,
                                            "Actions": [
                                                {
                                                    "Type": "forward",
                                                    "ForwardConfig": {
                                                        "TargetGroups": [
                                                            {
                                                                "TargetGroupArn": fargate_target_group.target_group_arn,
                                                                "Weight": 1
                                                            },
                                                            {
                                                                "TargetGroupArn": lambda_target_group.target_group_arn,
                                                                "Weight": 0
                                                            }
                                                        ]
                                                    }
                                                }
                                            ]
                                        },
                                        iam_resources=["*"],
                                        result_path="$.result"
                                      )
                                     )

        is_fargate_active_choice.otherwise(sfn.Wait(self, "Wait", time=sfn.WaitTime.duration(Duration.seconds(5))).next(get_task_count_task))

        lambda_task = tasks.CallAwsService(self, "Lambda",
            service="elasticloadbalancingv2",
            action="modifyRule",
            parameters={
                "RuleArn": route_rule.listener_rule_arn,
                "Actions": [
                    {
                        "Type": "forward",
                        "ForwardConfig": {
                            "TargetGroups": [
                                {
                                    "TargetGroupArn": fargate_target_group.target_group_arn,
                                    "Weight": 0
                                },
                                {
                                    "TargetGroupArn": lambda_target_group.target_group_arn,
                                    "Weight": 1
                                }
                            ]
                        }
                    }
                ]
            },
            iam_resources=["*"],
            result_path="$.result"
        ).next(tasks.CallAwsService(self, "Drain ECS running task count",
            service="ecs",
            action="updateService",
            parameters={
                "Cluster": cluster.cluster_name,
                "Service": fargate_service.service_name,
                "DesiredCount": 0
            },
            iam_resources=["*"],
            result_path="$.result"
        ))

        choice_state = sfn.Choice(self, "Choose Target Compute")
        choice_state.when(sfn.Condition.string_equals("$.target", "fargate"), hydrate_ecs_task.next(get_task_count_task).next(is_fargate_active_choice))
        choice_state.otherwise(lambda_task)

        state_machine = sfn.StateMachine(self, "TargetSwapperStateMachine",
            definition_body=sfn.DefinitionBody.from_chainable(choice_state),
            type=sfn.StateMachineType.EXPRESS,
            role=state_machine_role
        )