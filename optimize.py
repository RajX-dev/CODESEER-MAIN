import os, re, glob

# 1. Update style.css
css_addition = """
/* Site Footer Styles */
.site-footer {
    padding: 40px 0;
    position: relative;
    z-index: 10;
}
.footer-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
    text-align: center;
}
.footer-links {
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
    justify-content: center;
    font-size: 14px;
}
.footer-links a {
    color: var(--text-secondary);
    text-decoration: none;
    transition: color 0.2s;
}
.footer-links a:hover {
    color: var(--primary-color);
}
.footer-socials {
    display: flex;
    gap: 24px;
    justify-content: center;
}
.footer-socials a {
    color: var(--text-secondary);
    text-decoration: none;
    font-size: 18px;
    transition: color 0.2s;
}
.footer-socials a:hover {
    color: var(--primary-color);
}
.footer-copyright {
    color: var(--text-secondary);
    font-size: 14px;
}
"""
with open('public/style.css', 'a', encoding='utf-8') as f:
    f.write(css_addition)

# New footer HTML
new_footer = """<footer>
        <div class="container footer-content site-footer">
            <div class="footer-links">
                <a href="about.html">About Us</a>
                <a href="contact.html">Contact Us</a>
                <a href="shipping-policy.html">Shipping Policy</a>
                <a href="refund-policy.html">Refund Policy</a>
                <a href="terms.html">Terms & Conditions</a>
                <a href="privacy.html">Privacy Policy</a>
            </div>
            <div class="footer-socials">
                <a href="https://github.com/RajX-dev/N3MO" target="_blank" rel="noopener noreferrer" aria-label="GitHub">
                    <i class="fa-brands fa-github"></i>
                </a>
                <a href="https://twitter.com/n3mo_ai" target="_blank" rel="noopener noreferrer" aria-label="Twitter">
                    <i class="fa-brands fa-x-twitter"></i>
                </a>
            </div>
            <p class="footer-copyright">&copy; 2026 N3MO Code Intelligence. All rights reserved.</p>
        </div>
    </footer>"""

# 2. Update HTML Files
html_files = glob.glob('public/*.html')
for html_file in html_files:
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Replace footer
    html = re.sub(r'<footer>.*?</footer\s*>', new_footer, html, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML comments
    html = re.sub(r'<!--(.*?)-->', '', html, flags=re.DOTALL)
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Processed {html_file}')

# 3. Update dashboard.js
with open('public/dashboard.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Very basic JS comment removal that avoids URLs (lookbehind for not :)
# Remove block comments
js = re.sub(r'/\*[\s\S]*?\*/', '', js)
# Remove single line comments that do not follow a colon (like in https://)
js = re.sub(r'(?<!:)//.*', '', js)

# Remove empty lines created by comment removal
js = os.linesep.join([s for s in js.splitlines() if s.strip()])

with open('public/dashboard.js', 'w', encoding='utf-8') as f:
    f.write(js)
print('Processed dashboard.js')
