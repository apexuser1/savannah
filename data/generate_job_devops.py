#!/usr/bin/env python3
"""
Generate Cloud DevOps Engineer Job Description PDF
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

def create_job_description():
    pdf_file = "/home/ubuntu/resume_job_matcher/test_data/job_cloud_devops_engineer.pdf"
    doc = SimpleDocTemplate(pdf_file, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor='#1a1a1a',
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    company_style = ParagraphStyle(
        'CompanyStyle',
        parent=styles['Normal'],
        fontSize=14,
        textColor='#2563eb',
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=13,
        textColor='#1a1a1a',
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        textColor='#374151',
        spaceAfter=10,
        alignment=TA_JUSTIFY,
        leading=14
    )
    
    # Title
    story.append(Paragraph("Senior Cloud DevOps Engineer", title_style))
    story.append(Paragraph("CloudScale Technologies", company_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Company Overview
    story.append(Paragraph("About CloudScale Technologies", heading_style))
    story.append(Paragraph(
        "CloudScale Technologies is a leading cloud infrastructure and platform services provider, "
        "helping Fortune 500 companies and innovative startups scale their applications globally. "
        "With over 2,000 employees across 15 countries, we manage cloud infrastructure for more than "
        "5,000 enterprise clients. Our engineering team is at the forefront of cloud-native technologies, "
        "automation, and DevOps excellence.",
        body_style
    ))
    
    # Position Overview
    story.append(Paragraph("Position Overview", heading_style))
    story.append(Paragraph(
        "We are seeking a highly skilled Senior Cloud DevOps Engineer to join our Platform Engineering team. "
        "In this role, you will design, implement, and maintain scalable cloud infrastructure using "
        "infrastructure-as-code practices, container orchestration, and modern DevOps tooling. You will work "
        "closely with development teams to optimize CI/CD pipelines, improve deployment processes, and ensure "
        "high availability and performance of our cloud platforms.",
        body_style
    ))
    
    # Key Responsibilities
    story.append(Paragraph("Key Responsibilities", heading_style))
    responsibilities = [
        "Design and implement scalable, highly available cloud infrastructure on AWS or Azure using "
        "infrastructure-as-code tools (Terraform, CloudFormation)",
        
        "Build and maintain Kubernetes clusters for containerized applications, implementing best practices "
        "for security, networking, and resource management",
        
        "Develop and optimize CI/CD pipelines using Jenkins, GitLab CI, GitHub Actions, or similar tools "
        "to enable rapid, reliable software delivery",
        
        "Implement comprehensive monitoring and observability solutions using Prometheus, Grafana, ELK stack, "
        "and cloud-native monitoring tools",
        
        "Automate infrastructure provisioning, configuration management, and deployment processes using "
        "Python, Go, or Bash scripting",
        
        "Collaborate with development teams to optimize application architecture for cloud-native environments",
        
        "Implement and maintain security best practices including IAM policies, network security, "
        "secrets management, and compliance controls",
        
        "Participate in on-call rotation to ensure 24/7 availability of production systems",
        
        "Document infrastructure architecture, runbooks, and operational procedures"
    ]
    
    bullet_list = []
    for item in responsibilities:
        bullet_list.append(ListItem(Paragraph(item, body_style), leftIndent=20))
    
    story.append(ListFlowable(bullet_list, bulletType='bullet', start='bulletchar'))
    story.append(Spacer(1, 0.15*inch))
    
    # Required Skills and Qualifications
    story.append(Paragraph("Required Skills and Qualifications", heading_style))
    required_skills = [
        "<b>Cloud Platforms:</b> 3+ years of hands-on experience with AWS or Azure (or both), including "
        "compute, storage, networking, and managed services",
        
        "<b>Infrastructure as Code:</b> Expert-level proficiency with Terraform, CloudFormation, or Pulumi "
        "for managing cloud infrastructure",
        
        "<b>Container Orchestration:</b> Strong experience with Kubernetes (EKS, AKS, or self-managed), "
        "including deployment strategies, networking, and security",
        
        "<b>Containerization:</b> Extensive experience with Docker, including multi-stage builds, image "
        "optimization, and container security",
        
        "<b>Programming/Scripting:</b> Proficiency in Python or Go for automation, tooling, and infrastructure "
        "management. Bash scripting required",
        
        "<b>CI/CD Tools:</b> Strong experience building and maintaining CI/CD pipelines with Jenkins, GitLab CI, "
        "GitHub Actions, or CircleCI",
        
        "<b>Monitoring & Observability:</b> Experience implementing monitoring solutions with Prometheus, Grafana, "
        "CloudWatch, Datadog, or similar tools",
        
        "<b>Version Control:</b> Expert-level Git skills including branching strategies, code review, and GitOps practices",
        
        "<b>Experience:</b> 3-5 years in DevOps, Cloud Engineering, or Site Reliability Engineering roles",
        
        "<b>Education:</b> Bachelor's degree in Computer Science, Engineering, or related field (or equivalent experience)"
    ]
    
    skill_list = []
    for item in required_skills:
        skill_list.append(ListItem(Paragraph(item, body_style), leftIndent=20))
    
    story.append(ListFlowable(skill_list, bulletType='bullet', start='bulletchar'))
    story.append(Spacer(1, 0.15*inch))
    
    # Nice to Have
    story.append(Paragraph("Nice to Have", heading_style))
    nice_to_have = [
        "Multi-cloud experience (AWS + Azure + GCP)",
        "GitOps experience with ArgoCD or Flux",
        "Service mesh implementation (Istio, Linkerd)",
        "Infrastructure security and compliance expertise (SOC2, HIPAA, PCI-DSS)",
        "Experience with configuration management tools (Ansible, Chef, Puppet)",
        "Familiarity with serverless architectures (Lambda, Azure Functions)",
        "Certification: AWS Certified DevOps Professional, CKA, or CKAD",
        "Experience with disaster recovery and business continuity planning",
        "Knowledge of networking concepts (VPC, subnets, load balancers, DNS)"
    ]
    
    nice_list = []
    for item in nice_to_have:
        nice_list.append(ListItem(Paragraph(item, body_style), leftIndent=20))
    
    story.append(ListFlowable(nice_list, bulletType='bullet', start='bulletchar'))
    story.append(Spacer(1, 0.15*inch))
    
    # Benefits
    story.append(Paragraph("What We Offer", heading_style))
    benefits = [
        "Competitive salary range: $130,000 - $180,000 based on experience",
        "Comprehensive health, dental, and vision insurance",
        "401(k) with 6% company match",
        "Flexible remote work options (hybrid or fully remote)",
        "Professional development budget ($5,000/year) for courses, conferences, and certifications",
        "Latest MacBook Pro or Linux workstation",
        "Generous PTO policy (25 days) plus 10 paid holidays",
        "Stock options in a rapidly growing company",
        "Collaborative, learning-focused culture with regular tech talks and hackathons"
    ]
    
    benefit_list = []
    for item in benefits:
        benefit_list.append(ListItem(Paragraph(item, body_style), leftIndent=20))
    
    story.append(ListFlowable(benefit_list, bulletType='bullet', start='bulletchar'))
    story.append(Spacer(1, 0.15*inch))
    
    # Location
    story.append(Paragraph("Location", heading_style))
    story.append(Paragraph(
        "San Francisco, CA (Hybrid) or Remote (US & Canada)",
        body_style
    ))
    
    # How to Apply
    story.append(Paragraph("How to Apply", heading_style))
    story.append(Paragraph(
        "Please submit your resume, GitHub profile, and a brief cover letter explaining your experience "
        "with cloud infrastructure and DevOps practices to careers@cloudscaletech.com with the subject "
        "line 'Senior Cloud DevOps Engineer Application'.",
        body_style
    ))
    
    story.append(Spacer(1, 0.15*inch))
    
    # Equal Opportunity
    story.append(Paragraph(
        "<i>CloudScale Technologies is an equal opportunity employer. We celebrate diversity and are committed to "
        "creating an inclusive environment for all employees.</i>",
        body_style
    ))
    
    # Build PDF
    doc.build(story)
    print(f"✅ Created: {pdf_file}")

if __name__ == "__main__":
    create_job_description()
