import razorpay  # type: ignore
import sys

def main():
    key_id = input("Enter your Razorpay Key ID (rzp_test_... or rzp_live_...): ").strip()
    key_secret = input("Enter your Razorpay Key Secret: ").strip()
    
    if not key_id or not key_secret:
        print("Keys required. Exiting.")
        sys.exit(1)
        
    client = razorpay.Client(auth=(key_id, key_secret))

    # Base pricing
    # Starter = $10/mo, $102/year (15% off)
    # Pro = $49/mo, $558/year (5% off)
    # Team = $199/mo, $537/quarter (10% off)

    plans_to_create = [
        {"name": "Starter Monthly", "period": "monthly", "interval": 1, "amount_usd": 10},
        {"name": "Starter Yearly", "period": "yearly", "interval": 1, "amount_usd": 102},
        {"name": "Pro Monthly", "period": "monthly", "interval": 1, "amount_usd": 49},
        {"name": "Pro Yearly", "period": "yearly", "interval": 1, "amount_usd": 558},
        {"name": "Team Monthly", "period": "monthly", "interval": 1, "amount_usd": 199},
        # Razorpay doesn't have a 'quarterly' period natively, so we use 'monthly' with interval=3
        {"name": "Team Quarterly", "period": "monthly", "interval": 3, "amount_usd": 537},
    ]

    print("\nCreating plans on Razorpay...")
    created_plans = {}

    for plan in plans_to_create:
        try:
            # Note: Razorpay plans must be created in a specific currency.
            # If your base is INR, we multiply USD by 84 as an approximate setup rate.
            # (Subscriptions don't support dynamic forex on creation, they are fixed at creation time).
            # To allow UPI, we will create these plans in INR.
            amount_inr = int(plan["amount_usd"] * 84 * 100) # Amount in paise
            
            payload = {
                "period": plan["period"],
                "interval": plan["interval"],
                "item": {
                    "name": f"N3MO {plan['name']}",
                    "amount": amount_inr,
                    "currency": "INR",
                    "description": f"Subscription for {plan['name']}"
                }
            }
            
            resp = client.plan.create(payload)
            plan_id = resp["id"]
            created_plans[plan["name"]] = plan_id
            print(f"✅ Created {plan['name']} -> {plan_id}")
            
        except Exception as e:
            print(f"❌ Failed to create {plan['name']}: {e}")

    print("\n--- COPY PASTE THIS INTO n3mo/api_server.py ---")
    print("PLAN_MAPPINGS = {")
    for name, pid in created_plans.items():
        key_name = name.lower().replace(" ", "_")
        print(f'    "{key_name}": "{pid}",')
    print("}")

if __name__ == "__main__":
    main()
