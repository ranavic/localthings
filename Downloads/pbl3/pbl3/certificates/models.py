from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
import uuid
import hashlib
import json


class CertificateTemplate(models.Model):
    """Template for certificates issued by the platform."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Template appearance
    background_image = models.ImageField(upload_to='certificate_templates/', null=True, blank=True)
    logo = models.ImageField(upload_to='certificate_logos/', null=True, blank=True)
    primary_color = models.CharField(max_length=7, default='#000000', help_text=_("Hex color code"))
    secondary_color = models.CharField(max_length=7, default='#4A90E2', help_text=_("Hex color code"))
    font = models.CharField(max_length=50, default='Montserrat')
    
    # Certificate content
    title = models.CharField(max_length=200, default=_("Certificate of Completion"))
    subtitle = models.CharField(max_length=200, blank=True)
    body_text = models.TextField(help_text=_("Use {name}, {course}, {date}, etc. as placeholders"))
    
    # Signature images
    signature_1_image = models.ImageField(upload_to='certificate_signatures/', null=True, blank=True)
    signature_1_name = models.CharField(max_length=100, blank=True)
    signature_1_title = models.CharField(max_length=100, blank=True)
    
    signature_2_image = models.ImageField(upload_to='certificate_signatures/', null=True, blank=True)
    signature_2_name = models.CharField(max_length=100, blank=True)
    signature_2_title = models.CharField(max_length=100, blank=True)
    
    # Template metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Template type
    TYPE_CHOICES = [
        ('course', _('Course Completion')),
        ('program', _('Program Completion')),
        ('skill', _('Skill Certification')),
        ('achievement', _('Special Achievement')),
    ]
    certificate_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='course')
    
    class Meta:
        ordering = ['-is_active', 'name']
        
    def __str__(self):
        return f"{self.name} ({self.get_certificate_type_display()})"


class Certificate(models.Model):
    """Represents a certificate issued to a student."""
    # Unique identifier
    certificate_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Certificate information
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates')
    template = models.ForeignKey(CertificateTemplate, on_delete=models.PROTECT)
    title = models.CharField(max_length=200)
    
    # Course/program reference
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True)
    program = models.CharField(max_length=200, blank=True, help_text=_("For program certificates"))
    
    # Certificate details
    description = models.TextField(blank=True)
    issue_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    # Certificate status
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('issued', _('Issued')),
        ('revoked', _('Revoked')),
        ('expired', _('Expired')),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    
    # Certificate files
    pdf_file = models.FileField(upload_to='certificates/', null=True, blank=True)
    image_file = models.ImageField(upload_to='certificates/', null=True, blank=True)
    
    # Verification
    verification_code = models.CharField(max_length=64, blank=True, help_text=_("Unique verification code"))
    
    # Blockchain record
    blockchain_record = models.OneToOneField(
        'BlockchainRecord', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='certificate'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    revocation_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-issue_date']
        
    def __str__(self):
        return f"Certificate {self.certificate_id} for {self.recipient.username}"
    
    def save(self, *args, **kwargs):
        # Generate verification code if not present
        if not self.verification_code:
            self.verification_code = self.generate_verification_code()
            
        super().save(*args, **kwargs)
    
    def generate_verification_code(self):
        """Generate a unique verification code for this certificate."""
        data = f"{self.certificate_id}{self.recipient.id}{self.issue_date.timestamp()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def generate_certificate_hash(self):
        """Generate a hash of the certificate data for blockchain storage."""
        certificate_data = {
            'certificate_id': str(self.certificate_id),
            'recipient_id': self.recipient.id,
            'recipient_name': self.recipient.get_full_name(),
            'title': self.title,
            'course_id': self.course.id if self.course else None,
            'course_name': self.course.title if self.course else None,
            'program': self.program,
            'issue_date': self.issue_date.isoformat(),
            'verification_code': self.verification_code,
        }
        
        data_json = json.dumps(certificate_data, sort_keys=True)
        return hashlib.sha256(data_json.encode()).hexdigest()
    
    def issue(self):
        """Issue the certificate and record it on the blockchain."""
        if self.status == 'draft':
            self.status = 'issued'
            
            # Create blockchain record if not exists
            if not hasattr(self, 'blockchain_record'):
                hash_value = self.generate_certificate_hash()
                
                blockchain_record = BlockchainRecord.objects.create(
                    data_hash=hash_value,
                    data_type='certificate',
                    status='pending'
                )
                
                self.blockchain_record = blockchain_record
                
            self.save()
            
            # Trigger blockchain transaction
            # In a real implementation, this would call a service to record on the blockchain
            # self.blockchain_record.record_on_blockchain()
            
            return True
        return False
    
    def revoke(self, reason=''):
        """Revoke the certificate."""
        if self.status == 'issued':
            self.status = 'revoked'
            self.revocation_reason = reason
            self.save()
            
            # Update blockchain record
            if self.blockchain_record:
                self.blockchain_record.revoke()
                
            return True
        return False
    
    def check_expiry(self):
        """Check if the certificate has expired."""
        if self.expiry_date and timezone.now() >= self.expiry_date:
            self.status = 'expired'
            self.save(update_fields=['status'])
            return True
        return False
        
    @property
    def is_valid(self):
        """Check if the certificate is valid."""
        if self.status == 'expired':
            return False
        elif self.status == 'revoked':
            return False
        elif self.status == 'issued':
            self.check_expiry()  # Update status if expired
            return self.status == 'issued'
        return False
    
    @property
    def blockchain_verified(self):
        """Check if the certificate is verified on the blockchain."""
        return self.blockchain_record and self.blockchain_record.status == 'confirmed'
    
    @property
    def verification_url(self):
        """Get the verification URL for this certificate."""
        from django.urls import reverse
        return reverse('certificates:verify', args=[self.verification_code])


class BlockchainRecord(models.Model):
    """Record of blockchain transactions for certificates."""
    # Unique identifier
    record_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Blockchain data
    data_hash = models.CharField(max_length=64, help_text=_("SHA-256 hash of the data"))
    blockchain_txid = models.CharField(max_length=100, blank=True, help_text=_("Blockchain transaction ID"))
    blockchain_network = models.CharField(max_length=50, default='ethereum_testnet')
    
    # Record type
    data_type = models.CharField(max_length=50, default='certificate')
    
    # Record status
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('confirmed', _('Confirmed')),
        ('failed', _('Failed')),
        ('revoked', _('Revoked')),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    
    # Additional data
    metadata = models.JSONField(default=dict, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.data_type} record {self.record_id} - {self.status}"
    
    def record_on_blockchain(self):
        """Record this data on the blockchain."""
        # In a real implementation, this would use web3.py or another library
        # to submit the transaction to the blockchain
        
        try:
            # Placeholder for blockchain integration
            # txid = blockchain_service.submit_hash(self.data_hash)
            
            # For this demo:
            import time
            time.sleep(2)  # Simulate blockchain transaction time
            txid = f"0x{uuid.uuid4().hex}"
            
            self.blockchain_txid = txid
            self.status = 'confirmed'
            self.confirmed_at = timezone.now()
            self.save(update_fields=['blockchain_txid', 'status', 'confirmed_at'])
            return True
            
        except Exception as e:
            self.status = 'failed'
            self.error_message = str(e)
            self.retry_count += 1
            self.save(update_fields=['status', 'error_message', 'retry_count'])
            return False
    
    def verify_on_blockchain(self):
        """Verify that the record exists on the blockchain."""
        # In a real implementation, this would check the blockchain
        # to verify the record exists and matches our hash
        
        if not self.blockchain_txid:
            return False
            
        # Placeholder for blockchain verification logic
        # verified = blockchain_service.verify_hash(self.data_hash, self.blockchain_txid)
        
        # For this demo:
        verified = self.status == 'confirmed'
        
        return verified
    
    def revoke(self):
        """Mark this blockchain record as revoked."""
        self.status = 'revoked'
        self.revoked_at = timezone.now()
        
        # In a real implementation, this would record the revocation on the blockchain
        # blockchain_service.revoke_record(self.blockchain_txid)
        
        self.save(update_fields=['status', 'revoked_at'])
        return True


class CertificateVerification(models.Model):
    """Log of certificate verification attempts."""
    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE, related_name='verifications')
    
    # Verification details
    verification_time = models.DateTimeField(auto_now_add=True)
    verification_code = models.CharField(max_length=64)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    # Result
    is_valid = models.BooleanField()
    blockchain_verified = models.BooleanField(default=False)
    
    # Additional context
    verification_method = models.CharField(max_length=50, default='web')
    
    class Meta:
        ordering = ['-verification_time']
        
    def __str__(self):
        result = "Valid" if self.is_valid else "Invalid"
        return f"{result} verification of {self.certificate.certificate_id} at {self.verification_time}"


class CertificateShare(models.Model):
    """Tracks when and where users share their certificates."""
    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Share details
    PLATFORM_CHOICES = [
        ('linkedin', 'LinkedIn'),
        ('twitter', 'Twitter'),
        ('facebook', 'Facebook'),
        ('email', 'Email'),
        ('direct', 'Direct Link'),
        ('other', 'Other'),
    ]
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    shared_at = models.DateTimeField(auto_now_add=True)
    
    # Optional tracking
    recipient_email = models.EmailField(blank=True)
    custom_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-shared_at']
        
    def __str__(self):
        return f"{self.user.username} shared {self.certificate.title} on {self.platform}"
