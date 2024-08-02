import aws_cdk as core
import aws_cdk.assertions as assertions

from hybrid_construct.hybrid_construct_stack import HybridConstructStack

# example tests. To run these tests, uncomment this file along with the example
# resource in hybrid_construct/hybrid_construct_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = HybridConstructStack(app, "hybrid-construct")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
