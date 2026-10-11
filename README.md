# STACK IT — Customer Churn Predictor

A small Flask application that predicts whether a customer will churn. It runs
inference **two ways**, selected by one environment variable:

- `INFERENCE_MODE=local` — a scikit-learn model file bundled in the image (default)
- `INFERENCE_MODE=aws` — a deployed **Amazon SageMaker** endpoint (via boto3)

Built to run as a **Docker container on Amazon EC2**.

---

## What's inside

```
app/            Flask app (routes, feature schema, inference backends, UI)
model/          trained model + metadata (used in local mode)
train/          synthetic-data generator + training script
sagemaker/      SageMaker inference handler + endpoint deploy script
tests/          smoke tests
Dockerfile, docker-compose.yml, wsgi.py, requirements.txt, .env.example
```

## Endpoints

| Route              | Method | Purpose                                   |
|--------------------|--------|-------------------------------------------|
| `/`                | GET    | Web form                                  |
| `/predict`         | POST   | Form submit → result page (risk gauge)    |
| `/api/predict`     | POST   | JSON API (single record or `{"records":[...]}`) |
| `/health`          | GET    | Health check (used by Docker/ELB)         |

## Quick start (local, no Docker)

```bash
pip install -r requirements.txt
python train/train_model.py          # writes model/churn_model.joblib
./run_local.sh                       # serves on http://localhost:8080
```

## Quick start (Docker)

```bash
docker build -t stackit-churn-app:latest .
docker run -d -p 80:8080 --name churn stackit-churn-app:latest
# open http://localhost/
```

## Switch to AWS SageMaker inference

1. Deploy the model as an endpoint (from a machine with AWS creds):
   ```bash
   pip install sagemaker
   python sagemaker/deploy_endpoint.py \
     --role arn:aws:iam::<ACCOUNT_ID>:role/<SageMakerExecutionRole> \
     --bucket <your-sagemaker-bucket> \
     --endpoint-name stackit-churn-endpoint
   ```
2. Run the app pointed at it (no model file needed):
   ```bash
   docker run -d -p 80:8080 \
     -e INFERENCE_MODE=aws \
     -e SAGEMAKER_ENDPOINT_NAME=stackit-churn-endpoint \
     -e AWS_REGION=us-east-1 \
     stackit-churn-app:latest
   ```
   On EC2, give the instance an IAM role allowing `sagemaker:InvokeEndpoint`
   — no keys in the container.

## JSON API example

```bash
curl -X POST http://localhost/api/predict -H 'Content-Type: application/json' -d '{
  "gender":"Female","SeniorCitizen":"Yes","Partner":"No","Dependents":"No",
  "tenure":2,"PhoneService":"Yes","InternetService":"Fiber optic",
  "OnlineSecurity":"No","TechSupport":"No","StreamingTV":"Yes",
  "Contract":"Month-to-month","PaperlessBilling":"Yes",
  "PaymentMethod":"Electronic check","MonthlyCharges":95.0,"TotalCharges":190.0 }'
# -> {"churn": true, "probability": 0.9234}
```

## Kubernetes / EKS + CI/CD + ArgoCD (GitOps)

```
k8s/                    Kustomize manifests (namespace, deployment, service,
                        ingress[ALB], hpa, configmap, serviceaccount[IRSA])
.github/workflows/      GitHub Actions: test -> build & push to ECR -> bump
  ci-cd.yaml            the image tag in k8s/ (GitOps commit)
argocd/application.yaml ArgoCD Application that auto-syncs k8s/ to the cluster
```

Deploy straight to a cluster with kustomize:

```bash
kubectl apply -k k8s/           # local-mode by default
kubectl -n stackit-churn get pods,svc,ingress
```

**GitOps flow:** push to `main` → GitHub Actions builds/tests, pushes the image to
**ECR**, and commits a new image tag into `k8s/kustomization.yaml` → **ArgoCD**
sees the change and rolls it out to **EKS**. Toggle local vs SageMaker inference in
`k8s/configmap.yaml` (`INFERENCE_MODE`); in AWS mode, bind the `churn-sa` service
account to an IAM role via **IRSA**.

See the two deployment guides:
- **STACK IT_Churn_App_Deployment_Guide.pdf** — EC2 + Docker + SageMaker.
- **STACK IT_Churn_App_EKS_CICD_ArgoCD_Guide.pdf** — EKS + ECR + GitHub Actions + ArgoCD.

> The bundled model is trained on **synthetic** data for demonstration and is not
> a validated production model.
