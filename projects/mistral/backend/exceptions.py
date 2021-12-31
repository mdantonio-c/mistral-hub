class DiskQuotaException(Exception):
    """Exception for disk quota exceeding."""


class PostProcessingException(Exception):
    """Exception for post-processing failure."""


class InvalidLicenseException(Exception):
    """Exception for invalid license."""


class AccessToDatasetDenied(Exception):
    """Exception for permission denied to access arkimet dataset"""


class EmptyOutputFile(Exception):
    """Exception for empty output file"""


class WrongDbConfiguration(Exception):
    """Exception for misconfiguration in db"""


class UnexistingLicenseGroup(Exception):
    """Exception for a requested group of license that not exists"""


class UnAuthorizedUser(Exception):
    """Exception raised if a feature is reversed to logged users"""


class NetworkNotInLicenseGroup(Exception):
    """Exception raised if the requested network and the requested license group does not match"""


class MaxOutputSizeExceeded(Exception):
    """Exception raised if the output file size exceed the filesize allowed for each request"""


class JoinObservedExtraction(Exception):
    """Exception raised if at the end of an extraction of observed data the joining of output fails"""


class InvalidFiltersException(Exception):
    """Exception raised if the requested filters for extraction are invalid"""


class DeleteScheduleException(Exception):
    """Exception for Deletion of a schedule from celerybeat"""
