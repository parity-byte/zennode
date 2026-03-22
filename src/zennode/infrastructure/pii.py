import re

class PIIMasker:
    """
    Zero-Friction PII Masking Layer.
    Uses regex rules to detect and mask Social Security Numbers, Emails, and Phone Numbers
    before passing untrusted transcription audio to the LLM agent.
    """
    
    # Common PII Regex Patterns
    # Naive implementations for demonstration, in production use Microsoft Presidio
    EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    SSN_REGEX = r'\b\d{3}-\d{2}-\d{4}\b'
    PHONE_REGEX = r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    CARD_REGEX = r'\b(?:\d[ -]*?){13,16}\b'

    @classmethod
    def mask(cls, text: str) -> str:
        if not text:
            return ""
        
        # Scrub Emails
        text = re.sub(cls.EMAIL_REGEX, "[REDACTED_EMAIL]", text)
        
        # Scrub SSNs
        text = re.sub(cls.SSN_REGEX, "[REDACTED_SSN]", text)
        
        # Scrub Phones
        text = re.sub(cls.PHONE_REGEX, "[REDACTED_PHONE]", text)
        
        # Scrub Cards
        text = re.sub(cls.CARD_REGEX, "[REDACTED_CARD]", text)
        
        return text
