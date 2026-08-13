# Getting Started with DevOps Learn

`devops-learn` is an AI-assisted DevOps learning CLI that guides you through a security-gated Azure deployment lifecycle using real engineering tools.

## Installation

You can install `devops-learn` in an isolated virtual environment from the wheel, or in development mode.

### Production Install (from wheel)
```bash
python -m venv venv
source venv/bin/activate
pip install devops_learn-0.2.0-py3-none-any.whl
```

### Development Install (from source)
```bash
git clone https://github.com/howlcipher/DevOps-Learn-by-Doing.git
cd DevOps-Learn-by-Doing
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## The Workflow

The core philosophy of `devops-learn` is to move from simulation to real execution in controlled steps. 
The recommended progression is:

### 1. Check Readiness
Start by checking your system capabilities:
```bash
devops-learn doctor
```
Install any missing prerequisites (Docker, Terraform, Azure CLI, Trivy, Conftest) according to the output.

### 2. Set Up Learner Profile (Optional)
Configure your experience level to customize AI explanations:
```bash
devops-learn profile --set docker=strong terraform=beginner
```

### 3. Understand Your Workload
Initialize the project context and get AI-assisted architecture recommendations:
```bash
devops-learn init .
```

### 4. Build Locally
Run the real local vertical slice (pytest, flake8, and local Docker build):
```bash
devops-learn local .
```

### 5. Secure
Scan your code and configurations with Trivy and Conftest:
```bash
devops-learn security scan .
```

### 6. Infrastructure as Code
Plan your Terraform configuration safely:
```bash
devops-learn terraform .
```

### 7. Deploy to Azure
Execute the real, approval-controlled Container Apps path:
```bash
devops-learn deploy .
```
*Note: Azure deployment remains IMPLEMENTED but AWAITING LIVE VERIFICATION until an actual acceptance run provides proof.*

### 8. Prove Your Work
Generate an engineering evidence report from your session:
```bash
devops-learn report
```

You can view your active configuration anytime using:
```bash
devops-learn config show
```
