#!/usr/bin/env python3
"""
Generate DevOps Candidate Resume PDF
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib import colors

def create_resume():
    pdf_file = "/home/ubuntu/resume_job_matcher/test_data/resume_devops_candidate.pdf"
    doc = SimpleDocTemplate(pdf_file, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.6*inch, bottomMargin=0.6*inch)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    name_style = ParagraphStyle(
        'NameStyle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor='#1a1a1a',
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    contact_style = ParagraphStyle(
        'ContactStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor='#4b5563',
        spaceAfter=15,
        alignment=TA_CENTER
    )
    
    section_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=13,
        textColor='#1f2937',
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold',
        borderWidth=1,
        borderColor='#2563eb',
        borderPadding=5,
        backColor='#eff6ff'
    )
    
    heading_style = ParagraphStyle(
        'SubHeading',
        parent=styles['Normal'],
        fontSize=11,
        textColor='#1f2937',
        spaceAfter=4,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor='#374151',
        spaceAfter=6,
        leading=13
    )
    
    body_justify_style = ParagraphStyle(
        'BodyJustifyStyle',
        parent=body_style,
        alignment=TA_JUSTIFY
    )
    
    # Header - Name
    story.append(Paragraph("MICHAEL CHEN", name_style))
    
    # Contact Info
    contact_info = "San Francisco, CA | (415) 555-0147 | michael.chen@email.com | linkedin.com/in/michaelchen | github.com/mchen-devops"
    story.append(Paragraph(contact_info, contact_style))
    
    # Professional Summary
    story.append(Paragraph("PROFESSIONAL SUMMARY", section_style))
    summary_text = (
        "Results-driven Senior DevOps Engineer with 4+ years of experience designing and implementing "
        "scalable cloud infrastructure on AWS. Expert in infrastructure-as-code (Terraform), Kubernetes "
        "orchestration, and CI/CD pipeline automation. Proven track record of reducing deployment times by "
        "70% and improving system reliability to 99.9% uptime. Strong programming skills in Python and Bash, "
        "with deep expertise in containerization, monitoring, and cloud-native architectures. Passionate about "
        "automation, collaboration, and building robust DevOps practices."
    )
    story.append(Paragraph(summary_text, body_justify_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Technical Skills
    story.append(Paragraph("TECHNICAL SKILLS", section_style))
    
    skills_data = [
        ["<b>Cloud Platforms:</b>", "AWS (EC2, ECS, EKS, S3, RDS, Lambda, CloudFormation, CloudWatch), Azure basics"],
        ["<b>Containers & Orchestration:</b>", "Docker, Kubernetes, EKS, Helm, Kustomize"],
        ["<b>Infrastructure as Code:</b>", "Terraform (advanced), CloudFormation, Ansible"],
        ["<b>CI/CD Tools:</b>", "Jenkins, GitLab CI/CD, GitHub Actions, CircleCI"],
        ["<b>Monitoring & Observability:</b>", "Prometheus, Grafana, ELK Stack, CloudWatch, Datadog"],
        ["<b>Programming/Scripting:</b>", "Python (automation, boto3), Bash, Go (basic)"],
        ["<b>Version Control:</b>", "Git, GitHub, GitLab, Bitbucket, GitOps workflows"],
        ["<b>Databases:</b>", "PostgreSQL, MySQL, Redis, DynamoDB"],
        ["<b>Other Tools:</b>", "Linux/Unix, Nginx, HAProxy, Vault (secrets management)"]
    ]
    
    skills_table = Table(skills_data, colWidths=[1.6*inch, 5*inch])
    skills_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    story.append(skills_table)
    story.append(Spacer(1, 0.1*inch))
    
    # Professional Experience
    story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_style))
    
    # Job 1
    job1_header = Table([
        [Paragraph("<b>Senior DevOps Engineer</b>", heading_style), 
         Paragraph("<b>June 2022 - Present</b>", heading_style)]
    ], colWidths=[4.5*inch, 2.1*inch])
    job1_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(job1_header)
    
    story.append(Paragraph("<i>TechFlow Solutions, San Francisco, CA</i>", body_style))
    
    job1_bullets = [
        "Architected and deployed multi-region AWS infrastructure using Terraform, supporting 50+ microservices "
        "with 99.95% uptime and serving 10M+ daily requests",
        
        "Led migration to Kubernetes (EKS), reducing infrastructure costs by 35% and improving deployment "
        "frequency from weekly to multiple times per day",
        
        "Built comprehensive CI/CD pipelines using Jenkins and GitLab CI, reducing deployment time from 2 hours "
        "to 15 minutes through automated testing, security scanning, and canary deployments",
        
        "Implemented centralized monitoring and alerting with Prometheus, Grafana, and ELK stack, reducing "
        "mean time to detection (MTTD) by 60%",
        
        "Automated infrastructure provisioning using Python scripts and Terraform modules, enabling developers "
        "to self-service create environments in under 10 minutes",
        
        "Established GitOps practices with ArgoCD for declarative infrastructure management",
        
        "Mentored 3 junior DevOps engineers on Kubernetes, IaC best practices, and cloud architecture"
    ]
    
    for bullet in job1_bullets:
        story.append(Paragraph(f"• {bullet}", body_style))
    
    story.append(Spacer(1, 0.08*inch))
    
    # Job 2
    job2_header = Table([
        [Paragraph("<b>DevOps Engineer</b>", heading_style), 
         Paragraph("<b>July 2020 - May 2022</b>", heading_style)]
    ], colWidths=[4.5*inch, 2.1*inch])
    job2_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(job2_header)
    
    story.append(Paragraph("<i>CloudNative Innovations, San Jose, CA</i>", body_style))
    
    job2_bullets = [
        "Containerized 20+ legacy applications using Docker multi-stage builds, reducing image sizes by 60% "
        "and improving security posture",
        
        "Designed and implemented Kubernetes clusters on AWS EKS with auto-scaling, service mesh (basic Istio), "
        "and network policies for enhanced security",
        
        "Developed Terraform modules for reusable infrastructure components (VPC, RDS, EKS), adopted across "
        "5 product teams",
        
        "Built monitoring dashboards in Grafana for real-time visibility into application performance, "
        "infrastructure health, and cost optimization",
        
        "Implemented automated backup and disaster recovery procedures, achieving RPO of 15 minutes and "
        "RTO of 1 hour",
        
        "Collaborated with security team to implement IAM policies, secrets management with HashiCorp Vault, "
        "and compliance controls"
    ]
    
    for bullet in job2_bullets:
        story.append(Paragraph(f"• {bullet}", body_style))
    
    story.append(Spacer(1, 0.08*inch))
    
    # Job 3
    job3_header = Table([
        [Paragraph("<b>Junior DevOps Engineer</b>", heading_style), 
         Paragraph("<b>June 2019 - June 2020</b>", heading_style)]
    ], colWidths=[4.5*inch, 2.1*inch])
    job3_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(job3_header)
    
    story.append(Paragraph("<i>StartupHub Inc., San Francisco, CA</i>", body_style))
    
    job3_bullets = [
        "Automated deployment processes using Jenkins pipelines and Ansible playbooks, reducing manual effort "
        "by 80%",
        
        "Maintained and optimized AWS infrastructure (EC2, S3, RDS) for cost efficiency, saving $15K monthly",
        
        "Implemented log aggregation using ELK stack for centralized logging and troubleshooting",
        
        "Created comprehensive documentation and runbooks for infrastructure and deployment procedures",
        
        "Participated in on-call rotation, resolving production incidents with average resolution time of 45 minutes"
    ]
    
    for bullet in job3_bullets:
        story.append(Paragraph(f"• {bullet}", body_style))
    
    story.append(Spacer(1, 0.1*inch))
    
    # Certifications
    story.append(Paragraph("CERTIFICATIONS", section_style))
    certs = [
        "AWS Certified Solutions Architect - Associate (2021)",
        "Certified Kubernetes Administrator (CKA) - CNCF (2022)",
        "HashiCorp Certified: Terraform Associate (2023)"
    ]
    for cert in certs:
        story.append(Paragraph(f"• {cert}", body_style))
    
    story.append(Spacer(1, 0.1*inch))
    
    # Education
    story.append(Paragraph("EDUCATION", section_style))
    
    edu_header = Table([
        [Paragraph("<b>Bachelor of Science in Computer Science</b>", heading_style), 
         Paragraph("<b>2015 - 2019</b>", heading_style)]
    ], colWidths=[4.5*inch, 2.1*inch])
    edu_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(edu_header)
    
    story.append(Paragraph("<i>University of California, Berkeley</i>", body_style))
    story.append(Paragraph("GPA: 3.7/4.0 | Relevant Coursework: Operating Systems, Computer Networks, "
                          "Distributed Systems, Cloud Computing", body_style))
    
    story.append(Spacer(1, 0.1*inch))
    
    # Projects & Achievements
    story.append(Paragraph("KEY PROJECTS & ACHIEVEMENTS", section_style))
    
    projects = [
        "<b>Multi-Cloud Infrastructure Automation:</b> Developed Terraform modules for hybrid AWS/Azure "
        "deployment, enabling disaster recovery across cloud providers",
        
        "<b>Cost Optimization Initiative:</b> Led infrastructure cost analysis using CloudWatch and custom "
        "Python scripts, identifying $200K annual savings through rightsizing and reserved instances",
        
        "<b>Zero-Downtime Migration:</b> Orchestrated migration of monolithic application to microservices "
        "architecture on Kubernetes with zero customer impact",
        
        "<b>Open Source Contributions:</b> Contributed to Kubernetes documentation and Terraform AWS provider"
    ]
    
    for project in projects:
        story.append(Paragraph(f"• {project}", body_style))
    
    # Build PDF
    doc.build(story)
    print(f"✅ Created: {pdf_file}")

if __name__ == "__main__":
    create_resume()
