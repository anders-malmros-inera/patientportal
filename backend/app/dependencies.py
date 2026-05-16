from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_patient(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Saknar access token")

    personnummer = decode_access_token(credentials.credentials)
    if personnummer is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ogiltig eller utgangen token")
    return personnummer
