import re

def nameValidation(login):
    pat = re.compile(r"^[a-zA-Z0-9]{2,16}$")
    if re.fullmatch(pat, login):
        return True
    else:
        return False
    
def passwordValidation(password):
    pat = re.compile(
        r"^(?=.*[0-9])"            # Contains at least one digit
        r"(?=.*[A-Z])"            # Contains at least one uppercase letter
        r"(?=.*[a-z])"            # Contains at least one lowercase letter
        r"(?=.*[!@#$%^&*()_+\[\]:;,.?~\\/-])" # Contains at least one special character
        r"[A-Za-z0-9!@#$%^&*()_+\[\]:;,.?~\\/-]{8,16}$" # Consists only of alphanumeric and special characters, and is between 8 to 16 characters
    )
    if re.fullmatch(pat, password):
        return True
    else:
        return False