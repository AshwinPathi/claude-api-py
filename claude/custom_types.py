import io
from typing import Union, Dict, List, Any, Tuple

####################################################################
#                                                                  #
#                         Request Types                            #
#                                                                  #
####################################################################

# Types for sending requests
JsonType = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
HeaderType = Dict[str, str]

# Types for form data specific information.
FormDataType = Dict[str, Union[str, Tuple[str, io.BufferedReader]]]




####################################################################
#                                                                  #
#                         API Types                                #
#                                                                  #
####################################################################

# An attachment type looks like the following:
# {
#   'file_size': int,
#   'file_name': str,
#   'file_type': str,
#   'extracted_conents': str
#   'totalPages': int [Optional]
# }
# TODO - consider making this a dataclass instead?
AttachmentType = Dict[str, str]
