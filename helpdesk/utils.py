def get_client_ip(request):
    """
    Retrieves the client's real IP address from the request headers,
    taking into account reverse proxies (e.g., Render).
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # The first IP in the list is the client's original IP
        ip_address = x_forwarded_for.split(',')[0].strip()
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    return ip_address
