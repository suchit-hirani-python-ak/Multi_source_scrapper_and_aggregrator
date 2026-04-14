class BaseException(Exception):
    def __init__(self,message: str,status_code: int = 500) -> None:
        self.status_code = status_code
        self.message = message

class BadRequest(BaseException):
    def __init__(self,message):
        super().__init__(message = message,status_code = 400)

class NotFound(BaseException):
    def __init__(self, message):
        super().__init__(message = message, status_code=404)

class ServerError(BaseException):
    def __init__(self,message = "server side error"):
        super().__init__(message = message, status_code = 500)
        
class Unauthorized(BaseException):
    def __init__(self, message: str="email or password is wrong"):
        super().__init__(message=message, status_code=401)

class Forbidden(BaseException):
    def __init__(self,message="only admin allowed to access"):
        super().__init__(message=message, status_code=403)