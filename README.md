# CC Underwriting API

A machine learning API that predicts whether a credit card application should be approved or declined. Built with Python, deployed on Azure, automated with GitHub Actions.

---

## What Does This Do?

You send applicant details (income, credit score, age, etc.) to a REST API, and it returns:

| Field | Example | Meaning |
|-------|---------|---------|
| `decision` | `"Approved"` | Should we approve this applicant? |
| `approval_prob` | `0.68` | How confident is the model? (0 to 1) |
| `scorecard_score` | `545.5` | FICO-style credit score |
| `risk_band` | `"High Risk"` | Risk category |

**Model Performance:** AUC = 0.9955 (99.5% accuracy in ranking good vs bad applicants)

---

## Quick Test (Try It Now!)

The API is already live. Open your terminal and paste this:

```bash
curl -X POST https://ccuw-api-mahi80.azurewebsites.net/predict \
  -H "Content-Type: application/json" \
  -d '{
    "features": {
      "annual_income": 75000,
      "fico_score": 720,
      "age": 35,
      "debt_to_income_ratio": 0.25,
      "years_employed": 8,
      "total_assets": 150000,
      "total_liabilities": 30000,
      "num_credit_cards": 3,
      "savings_account_balance": 20000,
      "checking_account_balance": 5000
    }
  }'
```

**Response:**
```json
{
  "applicant_id": null,
  "decision": "Approved",
  "approval_prob": 0.68,
  "scorecard_score": 545.5,
  "risk_band": "High Risk"
}
```

> **Tip:** You do not need to send all 168 features. Send whatever you have - missing features default to 0.

Other endpoints:
```bash
# Health check - is the API running?
curl https://ccuw-api-mahi80.azurewebsites.net/health

# Model info - what metrics does it have?
curl https://ccuw-api-mahi80.azurewebsites.net/model

# Interactive API docs (Swagger UI) - try it in your browser!
# Open: https://ccuw-api-mahi80.azurewebsites.net/docs
```

---

## How It Works (Architecture)

```
You push code to GitHub
       |
       v
GitHub Actions runs automatically
       |
       +---> Installs Python packages
       +---> Logs into Azure (no passwords needed - uses OIDC tokens)
       +---> Trains the ML model on 5,000 applications
       +---> Logs metrics (AUC, F1, etc.) to Azure ML Studio
       +---> Deploys the API to Azure Web App
       |
       v
API is live at https://ccuw-api-mahi80.azurewebsites.net
       |
       v
Anyone can call POST /predict to get underwriting decisions
```

**Every push to the `main` branch automatically retrains and redeploys.** No manual steps needed after initial setup.

---

## Project Files

```
simplewebapp/
|
+-- app.py                              # The API server (FastAPI)
+-- train.py                            # Model training script
+-- requirements.txt                    # Python packages needed
+-- cc_underwriting_5k_stratified11.csv # Training data (5,000 applications)
+-- .gitignore                          # Files Git should ignore
|
+-- model/                              # Trained model files
|   +-- rf/model.pkl                    # The actual model (Random Forest)
|   +-- features.json                   # List of 168 feature names
|   +-- scaler.json                     # Normalization parameters
|   +-- metrics.json                    # Model performance numbers
|
+-- .github/
    +-- workflows/
        +-- deploy.yml                  # CI/CD pipeline definition
```

---

## Complete Setup Guide (From Zero)

> **Who is this for?** Anyone setting this up for the first time. Every command is included. Copy-paste and run them one by one.

---

### Prerequisites: Install These Tools First

You need 4 tools. If you already have them, skip to Step 1.

**1. Azure CLI** (talks to Azure from your terminal)
```bash
# Windows (run in PowerShell as Administrator):
winget install Microsoft.AzureCLI

# Mac:
brew install azure-cli

# Linux:
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```
Verify: `az version` should show a version number.

**2. GitHub CLI** (talks to GitHub from your terminal)
```bash
# Windows:
winget install GitHub.cli

# Mac:
brew install gh

# Linux:
sudo apt install gh
```
Verify: `gh version` should show a version number.

**3. Git** (version control)
```bash
# Windows: download from https://git-scm.com/download/win
# Mac:
xcode-select --install
# Linux:
sudo apt install git
```
Verify: `git --version` should show a version number.

**4. Python 3.11+** (for local development only)
```bash
# Download from https://python.org/downloads
```
Verify: `python --version` should show 3.11 or higher.

---

### Step 1: Login to Azure

This connects your terminal to your Azure account.

```bash
# Opens a browser window - sign in with your Azure credentials
az login
```

After logging in, verify your account:
```bash
az account show --query "{name:name, subscriptionId:id, tenantId:tenantId}" -o table
```

You will see something like:
```
Name                  SubscriptionId                        TenantId
--------------------  ------------------------------------  ------------------------------------
Azure subscription 1  3a72be92-287b-4f1e-840a-5e3e71100139  2b32b1fa-7899-482e-a6de-be99c0ff5516
```

**Write down your Subscription ID and Tenant ID.** You will need them later.

If you have multiple subscriptions, set the right one:
```bash
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

---

### Step 2: Login to GitHub CLI

```bash
# Opens a browser window - sign in with your GitHub credentials
gh auth login
```
Choose: GitHub.com > HTTPS > Login with a web browser

Verify:
```bash
gh auth status
```

---

### Step 3: Create a Resource Group

A resource group is like a folder in Azure. All your resources go inside it.

```bash
az group create --name zerotohero --location eastus
```

Verify:
```bash
az group show --name zerotohero --query "{name:name, location:location}" -o table
```

---

### Step 4: Create an App Service Plan

This is the virtual server that will run your API. Think of it as "renting a computer in the cloud."

```bash
az appservice plan create \
  --name ccuw-plan \
  --resource-group zerotohero \
  --sku B2 \
  --is-linux \
  --location uksouth
```

> **Got a quota error?** Try a different region: replace `uksouth` with `westeurope`, `centralus`, or `eastus2`

Verify:
```bash
az appservice plan show --name ccuw-plan --resource-group zerotohero \
  --query "{name:name, sku:sku.name}" -o table
```

---

### Step 5: Create the Web App

This is your actual API application.

```bash
az webapp create \
  --name ccuw-api-mahi80 \
  --resource-group zerotohero \
  --plan ccuw-plan \
  --runtime "PYTHON:3.11"
```

> **Name taken?** The web app name must be globally unique. If `ccuw-api-mahi80` is taken, try `ccuw-api-YOURNAME` instead.

Enable auto-build (so Azure installs Python packages during deployment):
```bash
az webapp config appsettings set \
  --name ccuw-api-mahi80 \
  --resource-group zerotohero \
  --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

Verify:
```bash
az webapp show --name ccuw-api-mahi80 --resource-group zerotohero \
  --query "{name:name, url:defaultHostName}" -o table
```

Your API will be at: `https://ccuw-api-mahi80.azurewebsites.net`

---

### Step 6: Create Azure ML Workspace (for Experiment Tracking)

This gives you a dashboard at [ml.azure.com](https://ml.azure.com) to see model performance over time.

**6a. Create a storage account** (Azure ML needs somewhere to store data):
```bash
az storage account create \
  --name ccuwmlflowstorage \
  --resource-group zerotohero \
  --location uksouth \
  --sku Standard_LRS
```

**6b. Create a Key Vault** (Azure ML needs somewhere to store secrets):
```bash
az keyvault create \
  --name ccuw-mlflow-kv \
  --resource-group zerotohero \
  --location uksouth
```

**6c. Create App Insights** (for monitoring):
```bash
az rest --method PUT \
  --url "https://management.azure.com/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/zerotohero/providers/Microsoft.Insights/components/ccuw-mlflow-ai?api-version=2020-02-02" \
  --body '{"location":"uksouth","kind":"web","properties":{"Application_Type":"web"}}'
```

> **Important:** Replace `YOUR_SUBSCRIPTION_ID` with the value from Step 1.

**6d. Create the ML Workspace.** Save this JSON as a file called `ml_deploy.json`:

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "resources": [
    {
      "type": "Microsoft.MachineLearningServices/workspaces",
      "apiVersion": "2024-04-01",
      "name": "ccuw-mlflow",
      "location": "uksouth",
      "identity": { "type": "SystemAssigned" },
      "properties": {
        "storageAccount": "/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/zerotohero/providers/Microsoft.Storage/storageAccounts/ccuwmlflowstorage",
        "keyVault": "/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/zerotohero/providers/Microsoft.KeyVault/vaults/ccuw-mlflow-kv",
        "applicationInsights": "/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/zerotohero/providers/microsoft.insights/components/ccuw-mlflow-ai",
        "friendlyName": "ccuw-mlflow"
      }
    }
  ]
}
```

> **Important:** Replace ALL THREE occurrences of `YOUR_SUBSCRIPTION_ID` in the JSON above.

Then deploy it:
```bash
az deployment group create \
  --resource-group zerotohero \
  --template-file ml_deploy.json
```

This takes about 2-3 minutes. When it says `"provisioningState": "Succeeded"`, you are good.

---

### Step 7: Set Up OIDC Authentication (GitHub <-> Azure)

This lets GitHub Actions deploy to Azure **without passwords**. It uses modern token-based auth (OIDC).

**7a. Create an App Registration** (an identity for GitHub Actions):
```bash
CLIENT_ID=$(az ad app create --display-name github-ccuw --query appId -o tsv)
echo "=== YOUR CLIENT ID: $CLIENT_ID ==="
```

**Save that CLIENT_ID!** You will need it in the next steps and for GitHub secrets.

**7b. Create a Federated Credential** (the trust link between GitHub and Azure):
```bash
az ad app federated-credential create \
  --id "$CLIENT_ID" \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:mahi80/simplewebapp:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

> **Important:** Replace `mahi80/simplewebapp` with YOUR GitHub username/repo if different.

**7c. Create a Service Principal** (gives the app registration actual permissions):
```bash
az ad sp create --id "$CLIENT_ID"
```

**7d. Get the Service Principal Object ID:**
```bash
SP_OBJ_ID=$(az ad sp show --id "$CLIENT_ID" --query id -o tsv)
echo "=== SP Object ID: $SP_OBJ_ID ==="
```

**7e. Give it Contributor access** to your resource group:
```bash
ROLE_ID=$(python -c "import uuid; print(uuid.uuid4())")

az rest --method PUT \
  --url "https://management.azure.com/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/zerotohero/providers/Microsoft.Authorization/roleAssignments/${ROLE_ID}?api-version=2022-04-01" \
  --body "{\"properties\":{\"roleDefinitionId\":\"/subscriptions/YOUR_SUBSCRIPTION_ID/providers/Microsoft.Authorization/roleDefinitions/b24988ac-6180-42a0-ab88-20f7382dd24c\",\"principalId\":\"${SP_OBJ_ID}\",\"principalType\":\"ServicePrincipal\"}}"
```

> **Important:** Replace `YOUR_SUBSCRIPTION_ID` (appears twice in the URL and body).

---

### Step 8: Create the GitHub Repository and Add Code

**8a. Create a new repo on GitHub** (if you have not already):
```bash
gh repo create simplewebapp --public --clone
cd simplewebapp
```

**8b. Unzip the project files and copy them in:**

```bash
# On Mac/Linux:
unzip /path/to/ccuw-simple.zip -d /tmp/ccuw-extract
cp -r /tmp/ccuw-extract/ccuw-simple/* .
cp -r /tmp/ccuw-extract/ccuw-simple/.github .
cp /tmp/ccuw-extract/ccuw-simple/.gitignore .

# On Windows (PowerShell):
Expand-Archive -Path "C:\path\to\ccuw-simple.zip" -DestinationPath "C:\tmp\ccuw-extract"
Copy-Item -Recurse "C:\tmp\ccuw-extract\ccuw-simple\*" .
Copy-Item -Recurse "C:\tmp\ccuw-extract\ccuw-simple\.github" .
Copy-Item "C:\tmp\ccuw-extract\ccuw-simple\.gitignore" .
```

---

### Step 9: Set the 6 GitHub Secrets

These are encrypted values that your CI/CD pipeline reads during deployment. Run each command:

```bash
# 1. The Client ID from Step 7a
gh secret set AZURE_CLIENT_ID --body "YOUR_CLIENT_ID"

# 2. Your Tenant ID from Step 1
gh secret set AZURE_TENANT_ID --body "YOUR_TENANT_ID"

# 3. Your Subscription ID from Step 1
gh secret set AZURE_SUBSCRIPTION_ID --body "YOUR_SUBSCRIPTION_ID"

# 4. Your Web App name from Step 5
gh secret set AZURE_WEBAPP_NAME --body "ccuw-api-mahi80"

# 5. The ML Workspace name from Step 6
gh secret set AZURE_ML_WORKSPACE --body "ccuw-mlflow"

# 6. The resource group name
gh secret set AZURE_ML_RESOURCE_GROUP --body "zerotohero"
```

Verify all 6 are set:
```bash
gh secret list
```

You should see:
```
AZURE_CLIENT_ID          Updated 2026-04-08
AZURE_TENANT_ID          Updated 2026-04-08
AZURE_SUBSCRIPTION_ID    Updated 2026-04-08
AZURE_WEBAPP_NAME        Updated 2026-04-08
AZURE_ML_WORKSPACE       Updated 2026-04-08
AZURE_ML_RESOURCE_GROUP  Updated 2026-04-08
```

---

### Step 10: Push Code and Deploy!

```bash
git add .
git commit -m "feat: CC underwriting model + Azure Web App deploy"
git push origin main
```

**This push triggers everything automatically.** GitHub Actions will:
1. Install Python packages (~1 min)
2. Login to Azure using OIDC
3. Train the model (~1 min)
4. Print AUC = 0.9955 in the logs
5. Deploy to your Web App (~3 min)

Watch it live:
```bash
gh run watch
```

Or open in browser: `https://github.com/mahi80/simplewebapp/actions`

---

### Step 11: Verify Everything Works

Wait about 1-2 minutes after the pipeline finishes (the app needs to start up).

```bash
# 1. Is the API alive?
curl https://ccuw-api-mahi80.azurewebsites.net/health
# Expected: {"status":"ok"}

# 2. What model is running?
curl https://ccuw-api-mahi80.azurewebsites.net/model
# Expected: {"features":168,"metrics":{"auc":0.9955,"gini":0.9909,...}}

# 3. Test a real prediction
curl -X POST https://ccuw-api-mahi80.azurewebsites.net/predict \
  -H "Content-Type: application/json" \
  -d '{"features": {"annual_income": 75000, "fico_score": 720, "age": 35}}'
# Expected: {"decision":"Approved","approval_prob":0.68,...}

# 4. Open the interactive API docs in your browser
# https://ccuw-api-mahi80.azurewebsites.net/docs

# 5. Check MLflow experiments
# https://ml.azure.com -> select your workspace -> Experiments -> cc-underwriting
```

---

## What Gets Created in Azure

| Resource | Name | What It Does | Monthly Cost (approx) |
|----------|------|--------------|-----------------------|
| Resource Group | `zerotohero` | Folder for all resources | Free |
| App Service Plan | `ccuw-plan` | Virtual server (B2: 2 CPU, 3.5GB RAM) | ~$55/month |
| Web App | `ccuw-api-mahi80` | Runs the Python API | Included in plan |
| Storage Account | `ccuwmlflowstorage` | Stores ML experiment data | ~$1/month |
| Key Vault | `ccuw-mlflow-kv` | Stores ML workspace secrets | ~$0.03/operation |
| App Insights | `ccuw-mlflow-ai` | Monitoring and logging | Free tier |
| ML Workspace | `ccuw-mlflow` | MLflow experiment tracking UI | Free tier |
| App Registration | `github-ccuw` | GitHub-to-Azure auth (OIDC) | Free |

**To stop all costs:** Delete the App Service Plan (the only significant charge):
```bash
az appservice plan delete --name ccuw-plan --resource-group zerotohero --yes
```

**To delete everything:**
```bash
az group delete --name zerotohero --yes --no-wait
```

---

## API Reference

### GET /health
Returns API status.
```bash
curl https://ccuw-api-mahi80.azurewebsites.net/health
```
Response: `{"status": "ok"}`

### GET /model
Returns model metadata.
```bash
curl https://ccuw-api-mahi80.azurewebsites.net/model
```
Response:
```json
{"features": 168, "metrics": {"auc": 0.9955, "gini": 0.9909, "accuracy": 0.9621, "f1": 0.9621}}
```

### POST /predict
Send applicant data, get an underwriting decision.

**Request body:**
```json
{
  "applicant_id": "APP-001",
  "features": {
    "annual_income": 75000,
    "fico_score": 720,
    "age": 35,
    "debt_to_income_ratio": 0.25,
    "years_employed": 8
  }
}
```

- `applicant_id` is optional (for your tracking)
- `features` can include any subset of the 168 model features
- Missing features default to 0

**Response:**
```json
{
  "applicant_id": "APP-001",
  "decision": "Approved",
  "approval_prob": 0.6808,
  "scorecard_score": 545.5,
  "risk_band": "High Risk"
}
```

**Risk bands:**
| Score Range | Risk Band |
|-------------|-----------|
| < 500 | Very High Risk |
| 500 - 559 | High Risk |
| 560 - 619 | Medium Risk |
| 620 - 679 | Low Risk |
| 680 - 739 | Very Low Risk |
| 740+ | Excellent |

### Interactive Docs
Open in browser: [https://ccuw-api-mahi80.azurewebsites.net/docs](https://ccuw-api-mahi80.azurewebsites.net/docs)

This gives you a Swagger UI where you can test the API directly from your browser.

---

## Some Common Feature Names

You do not need all 168 features. Here are the most useful ones:

| Feature | Description | Example |
|---------|-------------|---------|
| `annual_income` | Yearly income | 75000 |
| `fico_score` | Credit score | 720 |
| `age` | Applicant age | 35 |
| `debt_to_income_ratio` | Total debt / income | 0.25 |
| `years_employed` | Years at current job | 8 |
| `total_assets` | Total asset value | 150000 |
| `total_liabilities` | Total debt amount | 30000 |
| `net_worth` | Assets minus liabilities | 120000 |
| `savings_account_balance` | Savings balance | 20000 |
| `checking_account_balance` | Checking balance | 5000 |
| `num_credit_cards` | Number of credit cards | 3 |
| `num_total_credit_accounts` | All credit accounts | 8 |
| `credit_history_length_months` | Credit history age | 120 |
| `num_delinquent_accounts` | Past-due accounts | 0 |
| `monthly_rent_mortgage` | Monthly housing cost | 1500 |

---

## CI/CD Pipeline Details

What happens when you `git push origin main`:

| Step | What Happens | Time |
|------|-------------|------|
| 1. Checkout | GitHub clones your repo | 5s |
| 2. Setup Python | Installs Python 3.11 on the runner | 10s |
| 3. Install deps | Runs `pip install -r requirements.txt` | 30s |
| 4. Azure Login | Authenticates via OIDC (no passwords) | 5s |
| 5. ML Extension | Installs `az ml` CLI extension | 20s |
| 6. MLflow URI | Gets tracking URL from Azure ML | 5s |
| 7. Train Model | Runs `train.py` - trains Random Forest | 60s |
| 8. Show Metrics | Prints AUC, Gini, F1 to the log | 1s |
| 9. Deploy | Uploads code to Azure Web App | 120s |
| **Total** | | **~4-6 min** |

---

## Local Development

Want to run the API on your own machine?

```bash
# 1. Clone the repo
git clone https://github.com/mahi80/simplewebapp.git
cd simplewebapp

# 2. Install dependencies
pip install -r requirements.txt

# 3. Train the model (saves to model/ folder)
python train.py

# 4. Start the API
uvicorn app:app --reload

# 5. Open http://localhost:8000/docs in your browser
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Quota error` when creating App Service Plan | Try a different region: `--location westeurope` |
| `ccuw-api-mahi80 already exists` | Pick a different name: `ccuw-api-YOURNAME` |
| GitHub Actions fails at "Login to Azure" | Check your 3 Azure secrets (CLIENT_ID, TENANT_ID, SUBSCRIPTION_ID) |
| GitHub Actions fails at "Train model" | Check the error log - usually a package version issue |
| API shows "Application Error" after deploy | Wait 2 minutes for startup. Check `SCM_DO_BUILD_DURING_DEPLOYMENT=true` is set |
| `parse_version` import error | Use `imbalanced-learn>=0.12.3` in requirements.txt |
| `model/rf already exists` error | Already fixed in train.py (it clears the directory) |
| MLflow artifact upload warning | Safe to ignore - metrics still log to Azure ML |
| `curl: connection refused` locally | Make sure uvicorn is running on port 8000 |

---

## Useful Links

| Resource | URL |
|----------|-----|
| Live API | https://ccuw-api-mahi80.azurewebsites.net |
| API Docs (Swagger) | https://ccuw-api-mahi80.azurewebsites.net/docs |
| GitHub Repo | https://github.com/mahi80/simplewebapp |
| GitHub Actions | https://github.com/mahi80/simplewebapp/actions |
| Azure ML Studio | https://ml.azure.com |
| Azure Portal | https://portal.azure.com |
