"""Deploy the bundled churn model as a real-time Amazon SageMaker endpoint.

Run this from a machine with AWS credentials and the SageMaker SDK:

    pip install sagemaker
    python sagemaker/deploy_endpoint.py \
        --role arn:aws:iam::<ACCOUNT_ID>:role/<SageMakerExecutionRole> \
        --bucket <your-sagemaker-bucket> \
        --endpoint-name stackit-churn-endpoint

It packages model/churn_model.joblib + sagemaker/inference.py into a
model.tar.gz, uploads it to S3, and stands up a SKLearn real-time endpoint.
Afterwards, point the Flask app at it:

    INFERENCE_MODE=aws
    SAGEMAKER_ENDPOINT_NAME=stackit-churn-endpoint
    AWS_REGION=<region>
"""
import argparse
import os
import tarfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def make_tarball(dst):
    """model.tar.gz must contain the model file at the root and the handler
    under code/ so the SKLearn container can find both."""
    with tarfile.open(dst, "w:gz") as tar:
        tar.add(os.path.join(ROOT, "model", "churn_model.joblib"), arcname="churn_model.joblib")
        tar.add(os.path.join(HERE, "inference.py"), arcname="code/inference.py")
        tar.add(os.path.join(ROOT, "requirements.txt"), arcname="code/requirements.txt")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", required=True, help="SageMaker execution role ARN")
    ap.add_argument("--bucket", required=True, help="S3 bucket for the model artifact")
    ap.add_argument("--endpoint-name", default="stackit-churn-endpoint")
    ap.add_argument("--instance-type", default="ml.t2.medium")
    ap.add_argument("--region", default=os.getenv("AWS_REGION", "us-east-1"))
    a = ap.parse_args()

    import boto3
    import sagemaker
    from sagemaker.sklearn.model import SKLearnModel

    sess = sagemaker.Session(boto3.Session(region_name=a.region))

    with tempfile.TemporaryDirectory() as tmp:
        tar_path = os.path.join(tmp, "model.tar.gz")
        make_tarball(tar_path)
        model_uri = sess.upload_data(tar_path, bucket=a.bucket, key_prefix="stackit-churn/model")
        print("uploaded model artifact:", model_uri)

    model = SKLearnModel(
        model_data=model_uri,
        role=a.role,
        entry_point="inference.py",
        source_dir=HERE,
        framework_version="1.2-1",   # SageMaker SKLearn container version
        sagemaker_session=sess,
    )
    predictor = model.deploy(
        initial_instance_count=1,
        instance_type=a.instance_type,
        endpoint_name=a.endpoint_name,
    )
    print("endpoint live:", predictor.endpoint_name)
    print("set INFERENCE_MODE=aws and SAGEMAKER_ENDPOINT_NAME=%s" % predictor.endpoint_name)


if __name__ == "__main__":
    main()
