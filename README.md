This script generates screenshots showing how to reset your password on a Plone Classic site.

Assumptions:
- The Plone site's outbound email is configured on the Mail control panel and the site is able to send email.
- There is already a Plone site user with the username `bonobo`.
- The user has a valid email address associated to it.
- You have access to that email, allowing you to receive the emailed password reset link.

The output is a guide in markdown, HTML and PDF formats.

To run this script:

`python plone_password_reset_capture.py --user bonobo --password chumpchump10@ --url http://localhost:8080/Plone`
