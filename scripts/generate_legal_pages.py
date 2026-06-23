import os

base_path = "c:/Users/Raj shekhar/Documents/raj/project/main project/n3mo/public"

html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | N3MO Code Intelligence</title>
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:ital,wght@0,300..700;1,300..700&family=Space+Grotesque:wght@500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .legal-page {{ padding: 120px 0 60px; min-height: 80vh; }}
        .legal-content {{ max-width: 800px; margin: 0 auto; background: rgba(255,255,255,0.02); padding: 40px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); }}
        .legal-content h1 {{ color: var(--accent); margin-bottom: 24px; font-size: 32px; }}
        .legal-content h2 {{ margin-top: 32px; margin-bottom: 16px; font-size: 24px; color: #fff; }}
        .legal-content p, .legal-content li {{ color: var(--text-secondary); line-height: 1.6; margin-bottom: 16px; }}
        .legal-content a {{ color: var(--accent); text-decoration: none; }}
        .legal-content a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <header>
        <div class="nav-container">
            <div class="logo">
                <a href="/"><img src="logo.svg" alt="N3MO Logo" style="height: 42px; width: auto;"></a>
            </div>
            <nav>
                <a href="/#features">Features</a>
                <a href="/#pricing">Pricing</a>
                <a href="/#docs">CLI & Docs</a>
            </nav>
            <div class="nav-cta">
                <a href="/dashboard.html" class="btn btn-secondary">Dashboard</a>
            </div>
        </div>
    </header>

    <section class="legal-page">
        <div class="container legal-content">
            <h1>{title}</h1>
            {content}
        </div>
    </section>

    <footer>
        <div class="container footer-content" style="flex-direction: column; align-items: center; gap: 24px;">
            <div style="display: flex; gap: 24px; flex-wrap: wrap; justify-content: center;">
                <a href="about.html">About Us</a>
                <a href="contact.html">Contact Us</a>
                <a href="shipping-policy.html">Shipping Policy</a>
                <a href="refund-policy.html">Refund Policy</a>
                <a href="terms.html">Terms & Conditions</a>
                <a href="privacy.html">Privacy Policy</a>
            </div>
            <div style="display: flex; gap: 24px;">
                <p>&copy; 2026 N3MO Code Intelligence. Licensed under AGPL-3.0.</p>
            </div>
        </div>
    </footer>
    <script src="script.js"></script>
</body>
</html>"""

pages = {
    "about.html": {
        "title": "About Us",
        "content": """
            <p><strong>Registered Name:</strong> Raj Shekhar</p>
            <p><strong>Vintage (Year Established):</strong> 2026</p>
            <p><strong>About N3MO:</strong> N3MO is an automated PR review and impact analysis tool that visualizes code changes and calculates blast radius to help engineering teams deploy safely. We parse ASTs, map call graphs, and trace transitive dependencies natively across 27+ languages.</p>
        """
    },
    "contact.html": {
        "title": "Contact Us",
        "content": """
            <p>We'd love to hear from you. Please reach out using the details below:</p>
            <ul>
                <li><strong>Registered Name:</strong> Raj Shekhar</li>
                <li><strong>Registered Operating Address:</strong> [Your Full Address Here, City, State, PIN, India]</li>
                <li><strong>Contact Number:</strong> +91 8218901056</li>
                <li><strong>Email ID:</strong> <a href="mailto:sraj4090ti@gmail.com">sraj4090ti@gmail.com</a></li>
                <li><strong>Website Address:</strong> <a href="https://n3mo.shop">https://n3mo.shop</a></li>
            </ul>
            <p>Our support team typically responds within 24-48 business hours.</p>
        """
    },
    "shipping-policy.html": {
        "title": "Shipping & Delivery Policy",
        "content": """
            <p><strong>Digital Delivery Only</strong></p>
            <p>N3MO is a Software as a Service (SaaS) and digital product. Therefore, no physical shipping of goods is involved.</p>
            <p><strong>Delivery Timelines:</strong> Upon successful confirmation of payment, your account access, subscription upgrades, and digital license keys are delivered <strong>instantly</strong> and automatically.</p>
            <p>License keys (for Enterprise offline use) are displayed directly on your dashboard upon purchase and are immediately valid.</p>
            <p>If you experience any delays or issues accessing your digital purchase, please contact us immediately at <a href="mailto:sraj4090ti@gmail.com">sraj4090ti@gmail.com</a>.</p>
        """
    },
    "refund-policy.html": {
        "title": "Refund and Cancellation Policy",
        "content": """
            <h2>Cancellations</h2>
            <p>You may cancel your N3MO subscription at any time from your dashboard. Upon cancellation, your subscription will not renew, but you will retain access to your paid features until the end of your current billing cycle.</p>
            <h2>Refunds</h2>
            <p>As N3MO is a digital product providing immediate access to software licenses and cloud services, all sales are considered final once the service has been provisioned.</p>
            <p>However, we offer a <strong>7-day refund window</strong> for the following scenarios:</p>
            <ul>
                <li>Duplicate charges due to payment gateway errors.</li>
                <li>Technical failures on our end that prevent you from using the service, which our support team cannot resolve within 48 hours.</li>
                <li>Accidental subscription renewals (provided no usage of the premium service has occurred since the renewal date).</li>
            </ul>
            <h2>How to Request a Refund</h2>
            <p>To request a refund, please email <a href="mailto:sraj4090ti@gmail.com">sraj4090ti@gmail.com</a> within 7 days of the transaction. Include your GitHub ID and the transaction receipt. Approved refunds will be processed and credited back to the original payment method within 5-7 business days.</p>
        """
    },
    "terms.html": {
        "title": "Terms and Conditions",
        "content": """
            <p>By accessing or using N3MO, you agree to be bound by these Terms and Conditions.</p>
            <h2>1. Provision of Service</h2>
            <p>N3MO provides code intelligence and PR impact analysis tools. The service is provided "as is" without warranties of any kind.</p>
            <h2>2. User Responsibilities</h2>
            <p>You agree to use the service legally and securely. You are responsible for safeguarding your GitHub tokens, license keys, and account access.</p>
            <h2>3. Payments and Billing</h2>
            <p>Payments are processed securely via our payment gateway partners. You agree to provide accurate billing information. Subscriptions auto-renew unless cancelled prior to the renewal date.</p>
            <h2>4. Dispute Resolution</h2>
            <p>Any disputes arising from these terms or the use of N3MO shall be governed by the laws of India, and subject to the exclusive jurisdiction of the courts in [Your City/State].</p>
            <h2>5. Limitation of Liability</h2>
            <p>In no event shall N3MO or Raj Shekhar be liable for any indirect, incidental, or consequential damages arising from the use or inability to use the service.</p>
        """
    },
    "privacy.html": {
        "title": "Privacy Policy",
        "content": """
            <p>Your privacy is critically important to us. This policy outlines how we handle your data.</p>
            <h2>1. Information We Collect</h2>
            <p>We collect basic information required to provide our service, including your GitHub Profile ID, username, email address, and avatar URL when you authenticate via GitHub OAuth. We also collect transaction data (handled securely by our payment processors).</p>
            <h2>2. Code and Telemetry</h2>
            <p>We do <strong>not</strong> store your proprietary source code. For SaaS PR checks, code is cloned ephemerally to a secure container, analyzed for AST impacts, and immediately deleted. Local CLI users run everything entirely on their own machines with zero external data transmission.</p>
            <h2>3. Information Sharing</h2>
            <p>We do not sell or rent your personal information to third parties. Information may be shared with payment processors or infrastructure providers strictly for the purpose of operating the N3MO service.</p>
            <h2>4. Security Measures</h2>
            <p>We employ industry-standard security measures including HTTPS, JWT-based authentication, and secure ephemeral containers to protect your data against unauthorized access.</p>
            <h2>5. Contact</h2>
            <p>For any privacy-related queries, please contact <a href="mailto:sraj4090ti@gmail.com">sraj4090ti@gmail.com</a>.</p>
        """
    }
}

for filename, data in pages.items():
    filepath = os.path.join(base_path, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_template.format(title=data["title"], content=data["content"]))

print("Generated compliance pages.")
