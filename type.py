from typing import TypedDict, Union, Literal, Optional, Any, Dict, List, Tuple
from enum import Enum

class WebsocktMessageType(TypedDict):
    type: Literal["link","get_json","get_audio"]
    payload: Union[str, Dict[str, Any], None]