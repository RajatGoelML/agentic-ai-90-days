

applications = [
   # -------- Strong Profile 1 --------
    {
        "loan_id": "L001",
        "loan_amount": 800000,
        "income": 2400000,          # Strong annual income
        "debt": 300000,             # Low existing debt
        "emi": 15000,
        "credit_score": 785,
        "years_operating": 8,
        "sector": "IT Services"
    },

    # -------- Strong Profile 2 --------
    {
        "loan_id": "L002",
        "loan_amount": 500000,
        "income": 1800000,
        "debt": 200000,
        "emi": 12000,
        "credit_score": 760,
        "years_operating": 6,
        "sector": "Healthcare"
    },

    # -------- Medium Risk 1 --------
    {
        "loan_id": "L003",
        "loan_amount": 1200000,
        "income": 2200000,
        "debt": 800000,
        "emi": 30000,
        "credit_score": 705,
        "years_operating": 4,
        "sector": "Retail"
    },

    # -------- Medium Risk 2 --------
    {
        "loan_id": "L004",
        "loan_amount": 1500000,
        "income": 2500000,
        "debt": 1000000,
        "emi": 42000,
        "credit_score": 690,
        "years_operating": 3,
        "sector": "Manufacturing"
    },

    # -------- Borderline / High Risk 1 --------
    {
        "loan_id": "L005",
        "loan_amount": 1800000,
        "income": 2000000,
        "debt": 1200000,
        "emi": 55000,
        "credit_score": 640,
        "years_operating": 2,
        "sector": "Construction"
    },

    # -------- Borderline / High Risk 2 --------
    {
        "loan_id": "L006",
        "loan_amount": 2000000,
        "income": 2100000,
        "debt": 1500000,
        "emi": 65000,
        "credit_score": 620,
        "years_operating": 1,
        "sector": "Hospitality"
    }
]

portfolio_state = {
    "capital_reserve": 10000000,
    "required_capital": 0,
    "risk_weighted_exposure": 0,
    "portfolio_results": [],
    "portfolio_metrics": {},
    "concentration_flags": [],
    "stress_test_results": {}
    }

def evaluate_loan(application):

    total_score = 0
    baseline_decision = None
    debt = application["debt"]
    income = application["income"]
    credit_score = application["credit_score"]
    emi_monthly = application["emi"]
    annual_income = application["income"]

    # we will check the debt , income and credit score if they are valid integers / float values to prceed else can through validation error

    dti_ratio = debt / income

    emi_ratio = 12*emi_monthly / annual_income

    if dti_ratio <= 0.25:   
       total_score += 30 
    elif dti_ratio <= 0.40:
       total_score += 25 
    elif dti_ratio <= 0.60:
       total_score += 15 
    else:
       total_score += 5    

    if emi_ratio <= 0.20:   
       total_score += 25 
    elif emi_ratio <= 0.35:
       total_score += 15 
    else:
       total_score += 5 

    if credit_score >= 750:   
       total_score += 30 
    elif credit_score <= 749:
       total_score += 20 
    elif  credit_score <= 699:
       total_score += 10   
    else:
       total_score += 5          


    if total_score >= 70:
       risk_tier = "LOW"
       baseline_decision = "APPROVE"
    elif total_score >= 55 and total_score <=69:
       risk_tier = "MEDIUM"
       baseline_decision = "REVIEW"
    else:
       risk_tier = "HIGH"  
       baseline_decision = "REJECT" 
             
    return{
           "loan_id": application["loan_id"],
           "loan_amount": application["loan_amount"],
           "score": total_score,
           "risk_tier": risk_tier,
           "baseline_decision": baseline_decision,
           "dti": dti_ratio,
           "emi_ratio": emi_ratio
    }

count_high = 0
count_medium = 0
count_low = 0

total_exposure = 0
approved_exposure = 0
total_score_sum = 0
valid_loan_count = 0

for app in applications:
    result = evaluate_loan(app)

    # Skip invalid loans
    # if result.get("status") == "ERROR":
    #     continue

    # Store per-loan result
    portfolio_state["portfolio_results"].append(result)

    total_exposure += result["loan_amount"]

    if result["baseline_decision"] == "APPROVE":
        approved_exposure += result["loan_amount"]

    total_score_sum += result["score"]
    valid_loan_count += 1

    if result["risk_tier"] == "HIGH":
        count_high += 1
    elif result["risk_tier"] == "MEDIUM":
        count_medium += 1
    else:
        count_low += 1


# Compute average safely
average_score = (
    total_score_sum / valid_loan_count
    if valid_loan_count > 0 else 0
)

portfolio_state["portfolio_metrics"] = {
    "total_exposure": total_exposure,
    "approved_exposure": approved_exposure,
    "average_score": average_score,
    "tier_distribution": {
        "LOW": count_low,
        "MEDIUM": count_medium,
        "HIGH": count_high
    }
}

count_high = 0
count_medium = 0
count_low = 0

total_exposure = 0
approved_exposure = 0
total_score_sum = 0
valid_loan_count = 0

for app in applications:
    result = evaluate_loan(app)

    # Skip invalid loans
    if result.get("status") == "ERROR":
        continue

    # Store per-loan result
    portfolio_state["portfolio_results"].append(result)

    total_exposure += result["loan_amount"]

    if result["baseline_decision"] == "APPROVE":
        approved_exposure += result["loan_amount"]

    total_score_sum += result["score"]
    valid_loan_count += 1

    if result["risk_tier"] == "HIGH":
        count_high += 1
    elif result["risk_tier"] == "MEDIUM":
        count_medium += 1
    else:
        count_low += 1


# Compute average safely
average_score = (
    total_score_sum / valid_loan_count
    if valid_loan_count > 0 else 0
)

portfolio_state["portfolio_metrics"] = {
    "total_exposure": total_exposure,
    "approved_exposure": approved_exposure,
    "average_score": average_score,
    "tier_distribution": {
        "LOW": count_low,
        "MEDIUM": count_medium,
        "HIGH": count_high
    }
}

# -----------------------------
# Concentration Detection
# -----------------------------

total_loans = len(portfolio_state["portfolio_results"])

high_count = 0
medium_count = 0
marginal_count = 0

sector_exposure = {}

for result in portfolio_state["portfolio_results"]:

    tier = result["risk_tier"]
    score = result["score"]
    amount = result["loan_amount"]

    # Count risk tiers
    if tier == "HIGH":
        high_count += 1
    elif tier == "MEDIUM":
        medium_count += 1

    # Detect marginal approvals (score 70–75)
    if 70 <= score <= 75:
        marginal_count += 1

    # Aggregate sector exposure
    sector = next(
        app["sector"]
        for app in applications
        if app["loan_id"] == result["loan_id"]
    )

    if sector not in sector_exposure:
        sector_exposure[sector] = 0

    sector_exposure[sector] += amount


# -----------------------------
# Apply Concentration Rules
# -----------------------------

# Rule 1: High Risk ≥ 30%
if total_loans > 0 and (high_count / total_loans) >= 0.30:
    portfolio_state["concentration_flags"].append("HIGH_RISK_CONCENTRATION")

# Rule 2: Medium + High ≥ 60%
if total_loans > 0 and ((high_count + medium_count) / total_loans) >= 0.60:
    portfolio_state["concentration_flags"].append("ELEVATED_PORTFOLIO_RISK")

# Rule 3: Sector Exposure ≥ 40% of total exposure
total_exposure = portfolio_state["portfolio_metrics"]["total_exposure"]

for sector, exposure in sector_exposure.items():
    if total_exposure > 0 and (exposure / total_exposure) >= 0.40:
        portfolio_state["concentration_flags"].append(
            f"SECTOR_CONCENTRATION_{sector}"
        )

# Rule 4: Marginal Approval Cluster
if marginal_count >= 2:
    portfolio_state["concentration_flags"].append("MARGINAL_APPROVAL_CLUSTER")


# -----------------------------
# Stress Test Simulation
# -----------------------------

stress_income_drop = 0.15  # 15% income reduction

stressed_risk_weighted_exposure = 0
stressed_results = []

for app in applications:

    stressed_income = app["income"] * (1 - stress_income_drop)

    # Recalculate ratios
    dti_ratio = app["debt"] / stressed_income
    emi_ratio = (app["emi"] * 12) / stressed_income

    total_score = 0

    # DTI scoring
    if dti_ratio <= 0.25:
        total_score += 30
    elif dti_ratio <= 0.40:
        total_score += 25
    elif dti_ratio <= 0.60:
        total_score += 15
    else:
        total_score += 5

    # EMI scoring
    if emi_ratio <= 0.20:
        total_score += 25
    elif emi_ratio <= 0.35:
        total_score += 15
    else:
        total_score += 5

    # Credit scoring (unchanged under stress)
    credit_score = app["credit_score"]

    if credit_score >= 750:
        total_score += 30
    elif credit_score >= 700:
        total_score += 20
    elif credit_score >= 650:
        total_score += 10
    else:
        total_score += 5

    # Assign stressed tier
    if total_score >= 70:
        tier = "LOW"
        weight = 0.5
    elif total_score >= 55:
        tier = "MEDIUM"
        weight = 1.0
    else:
        tier = "HIGH"
        weight = 1.5

    stressed_risk_weighted_exposure += app["loan_amount"] * weight

    stressed_results.append({
        "loan_id": app["loan_id"],
        "stressed_score": total_score,
        "stressed_tier": tier
    })


# Recalculate capital under stress
stressed_required_capital = 0.12 * stressed_risk_weighted_exposure

stressed_capital_buffer = (
    portfolio_state["capital_reserve"] - stressed_required_capital
)

portfolio_state["stress_test_results"] = {
    "stressed_risk_weighted_exposure": stressed_risk_weighted_exposure,
    "stressed_required_capital": stressed_required_capital,
    "stressed_capital_buffer": stressed_capital_buffer,
    "stressed_loan_results": stressed_results
}

# Stress flag
if stressed_capital_buffer < 0:
    portfolio_state["concentration_flags"].append("STRESS_CAPITAL_BREACH")


# -----------------------------
# Final Portfolio Governance Report
# -----------------------------

print("\n" + "="*60)
print("FINAL PORTFOLIO GOVERNANCE REPORT")
print("="*60)

metrics = portfolio_state["portfolio_metrics"]
stress = portfolio_state["stress_test_results"]
flags = portfolio_state["concentration_flags"]

print("\n--- Base Portfolio Metrics ---")
print(f"Total Exposure: ₹{metrics['total_exposure']}")
print(f"Approved Exposure: ₹{metrics['approved_exposure']}")
print(f"Average Risk Score: {round(metrics['average_score'], 2)}")
print(f"Risk Tier Distribution: {metrics['tier_distribution']}")
# print(f"Capital Buffer (Base): ₹{round(metrics['capital_buffer'], 2)}")

print("\n--- Stress Test Metrics (15% Income Shock) ---")
print(f"Stressed Risk-Weighted Exposure: ₹{round(stress['stressed_risk_weighted_exposure'], 2)}")
print(f"Stressed Required Capital: ₹{round(stress['stressed_required_capital'], 2)}")
print(f"Stressed Capital Buffer: ₹{round(stress['stressed_capital_buffer'], 2)}")

print("\n--- Concentration & Risk Flags ---")

if not flags:
    print("No concentration risks detected.")
else:
    for flag in flags:
        print(f"- {flag}")

# Final Portfolio Status Logic
if "CAPITAL_BUFFER_BREACH" in flags or "STRESS_CAPITAL_BREACH" in flags:
    portfolio_status = "CRITICAL"
elif "CAPITAL_BUFFER_CRITICAL" in flags:
    portfolio_status = "ELEVATED_RISK"
elif "HIGH_RISK_CONCENTRATION" in flags or "ELEVATED_PORTFOLIO_RISK" in flags:
    portfolio_status = "MODERATE_RISK"
else:
    portfolio_status = "STABLE"

print("\n--- Final Portfolio Status ---")
print(f"Portfolio Health Classification: {portfolio_status}")

print("="*60)    