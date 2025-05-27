from django.urls import path
from . import views

app_name = 'certificates'

urlpatterns = [
    # Certificate management
    path('', views.CertificateListView.as_view(), name='certificate_list'),
    path('<uuid:certificate_id>/', views.CertificateDetailView.as_view(), name='certificate_detail'),
    path('<uuid:certificate_id>/download/', views.DownloadCertificateView.as_view(), name='download_certificate'),
    path('<uuid:certificate_id>/share/', views.ShareCertificateView.as_view(), name='share_certificate'),
    
    # Certificate verification
    path('verify/', views.VerifyCertificateView.as_view(), name='verify_certificate'),
    path('verify/<uuid:verification_code>/', views.VerificationResultView.as_view(), name='verification_result'),
    path('blockchain-record/<uuid:certificate_id>/', views.BlockchainRecordView.as_view(), name='blockchain_record'),
    
    # Certificate templates
    path('templates/', views.CertificateTemplateListView.as_view(), name='template_list'),
    path('templates/<int:template_id>/', views.CertificateTemplateDetailView.as_view(), name='template_detail'),
    
    # Certificate issuing
    path('issue/', views.IssueCertificateView.as_view(), name='issue_certificate'),
    path('issue/batch/', views.BatchIssueCertificatesView.as_view(), name='batch_issue'),
    
    # Certificate revocation
    path('<uuid:certificate_id>/revoke/', views.RevokeCertificateView.as_view(), name='revoke_certificate'),
    path('revocation-list/', views.RevocationListView.as_view(), name='revocation_list'),
    
    # Public certificate views
    path('public/<uuid:certificate_id>/', views.PublicCertificateView.as_view(), name='public_certificate'),
    path('showcase/', views.CertificateShowcaseView.as_view(), name='certificate_showcase'),
]
