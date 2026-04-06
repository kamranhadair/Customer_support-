# Troubleshooting Guide

## Cannot Log In / Account Access Issues

### Symptoms
- "Invalid credentials" error despite correct password
- Account shows as locked or suspended
- Two-factor authentication (2FA) code not accepted

### Solutions

1. **Reset your password:**
   - Visit app.example.com/forgot-password
   - Enter your registered email address
   - Check your inbox for a reset link (valid for 1 hour)

2. **Check account status:**
   - Log in from a different browser or incognito mode
   - Clear browser cache and cookies
   - Disable VPN/proxy — some regions may trigger security locks

3. **2FA issues:**
   - Ensure your device clock is synced (TOTP codes are time-sensitive)
   - Use a backup code from your Security Settings if authenticator is lost
   - Contact support if all backup codes are exhausted

4. **Account locked:**
   - After 10 failed login attempts, accounts are locked for 30 minutes
   - Contact support@example.com with your email and we'll unlock it

---

## API Integration Errors

### Error: 401 Unauthorized
- Your API key is missing, expired, or invalid
- Solution: Regenerate your API key in **Settings → API Keys**

### Error: 429 Too Many Requests
- You have exceeded your plan's rate limit
- Solution: Wait and retry with exponential backoff, or upgrade your plan

### Error: 500 Internal Server Error
- A temporary server issue
- Check our status page: status.example.com
- Retry after 5 minutes; if persistent, open a support ticket

---

## Billing & Payment Issues

### Payment Declined
- Check that your card details are correct in **Billing → Payment Methods**
- Ensure your card allows international transactions
- Try a different card or payment method

### Invoice Not Received
- Check your spam/junk folder
- Verify the billing email in **Settings → Profile**
- Download invoices from **Billing → Invoice History**

### Unexpected Charges
- Review the charge details in **Billing → Invoice History**
- Prorated charges appear when you upgrade mid-cycle
- Contact billing@example.com if you believe a charge is incorrect

---

## Data & Sync Issues

### Data Not Updating
1. Hard refresh the page (Ctrl+Shift+R / Cmd+Shift+R)
2. Log out and log back in
3. Check your browser console for JavaScript errors
4. If using the API, ensure you're reading from the correct endpoint

### Export/Import Failures
- Maximum file size: 50 MB for CSV and 25 MB for JSON
- Ensure the file encoding is UTF-8
- Verify your plan allows bulk export (Pro+ only)
