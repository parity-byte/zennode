import sys

import structlog

logger = structlog.get_logger(__name__)

def check_and_request_microphone_permission() -> bool:
    """
    Checks and requests macOS Microphone access via AVFoundation.
    Returns True if granted, False if denied.
    Does nothing on non-macOS systems.
    """
    if sys.platform != "darwin":
        return True
        
    try:
        import Foundation  # type: ignore
        from AVFoundation import AVCaptureDevice, AVMediaTypeAudio  # type: ignore
        
        status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)
        
        if status == 3: # AVAuthorizationStatusAuthorized
            return True
        if status in (1, 2): # Restricted or Denied
            logger.warning("microphone_permission_denied")
            return False
            
        # Status 0 = NotDetermined, need to prompt
        logger.info("requesting_microphone_permission")
        granted = [False]
        semaphore = Foundation.dispatch_semaphore_create(0)
        
        def handler(access_granted: bool) -> None:
            granted[0] = access_granted
            Foundation.dispatch_semaphore_signal(semaphore)

        AVCaptureDevice.requestAccessForMediaType_completionHandler_(AVMediaTypeAudio, handler)
        Foundation.dispatch_semaphore_wait(semaphore, Foundation.DISPATCH_TIME_FOREVER)
        
        return granted[0]
        
    except ImportError:
        logger.warning("pyobjc_not_installed_skipping_permission_check")
        return True
    except Exception as e:
        logger.warning("failed_to_request_microphone_permission", error=str(e))
        return True
