from django.urls import reverse


def set_google_profile_flags(strategy, details, backend, user=None, *args, **kwargs):
    """Social-auth pipeline step for Google logins.

    - Marks Google-based users as email-verified.
    - Flags in the session that the user may need to complete profile via wizard.
    """
    if backend.name != 'google-oauth2' or user is None:
        return

    request = strategy.request

    # Mark email as verified for Google users
    profile = getattr(user, 'userprofile', None)
    if profile is not None:
        if not profile.email_verified:
            profile.email_verified = True
            profile.save(update_fields=['email_verified'])
    
    # Store a flag in the session so post-login flow can redirect
    request.session['needs_google_profile_completion'] = True
