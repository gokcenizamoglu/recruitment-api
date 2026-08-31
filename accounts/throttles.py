from rest_framework.throttling import AnonRateThrottle


class RegistrationThrottle(AnonRateThrottle):
    scope = "register"


class LoginThrottle(AnonRateThrottle):
    scope = "login"
