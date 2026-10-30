from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RiskHelpDefinition, RiskReferenceValue, RiskTaxonomyFamily, RiskTaxonomyType

FAMILIES = [
    ("F01", "Governance & Architecture Decisions", "Gouvernance & Décisions d’architecture"),
    ("F02", "IT Assets & Technology Sustainability", "Patrimoine applicatif & technologique"),
    ("F03", "Resilience, Performance & Operability", "Résilience, Performance & Exploitabilité"),
    ("F04", "Data & Integration", "Données & Intégration"),
    ("F05", "Security, Compliance & Sovereignty", "Sécurité, Conformité & Souveraineté"),
    ("F06", "Third Parties & Technology Dependencies", "Tiers & Dépendances technologiques"),
    ("F07", "Strategy & Evolution of the IS", "Stratégie & Évolution du SI"),
    ("F08", "Project & Delivery", "Projet & Delivery"),
]

TYPES = [
    ("F01.01", "F01", "Deviation from architectural standards and principles", "Écart aux standards et principes d’architecture"),
    ("F01.02", "F01", "Gap between the approved architecture and the implemented solution", "Écart entre l’architecture validée et la solution mise en œuvre"),
    ("F01.03", "F01", "Implementing a solution without architectural validation", "Mise en œuvre d’une solution sans validation architecturale"),
    ("F02.01", "F02", "Accumulation of technical and architectural debt", "Accumulation de dette technique et architecturale"),
    ("F02.02", "F02", "Application functional overlap", "Recouvrement fonctionnel"),
    ("F02.03", "F02", "Incomplete or outdated knowledge of heritage", "Connaissance incomplète ou obsolète du patrimoine"),
    ("F02.04", "F02", "Systemic failure of the IS", "Défaillance systémique du SI"),
    ("F02.05", "F02", "Proliferation of solutions outside IT governance", "Prolifération de solutions hors gouvernance IT"),
    ("F02.06", "F02", "Technological obsolescence", "Obsolescence technologique"),
    ("F02.07", "F02", "Insufficient governance of the application lifecycle", "Gouvernance insuffisante du cycle de vie applicatif"),
    ("F03.01", "F03", "Late detection of incidents and damage", "Détection tardive des incidents et dégradations"),
    ("F03.02", "F03", "Inability to maintain or restore service after a failure", "Incapacité à maintenir ou rétablir le service après une défaillance"),
    ("F03.03", "F03", "Inability to absorb a surge", "Incapacité à absorber une montée en charge"),
    ("F04.01", "F04", "Data quality and integrity", "Altération de la qualité et de l’intégrité des données"),
    ("F04.02", "F04", "Failure of inter-application exchanges", "Défaillance des échanges inter-applicatifs"),
    ("F05.01", "F05", "Data protection non-compliance", "Non-conformité à la protection des données"),
    ("F05.02", "F05", "Compromise of systems or data", "Compromission des systèmes ou des données"),
    ("F05.03", "F05", "Insufficient control of sovereignty", "Maîtrise insuffisante de la souveraineté"),
    ("F06.01", "F06", "Failure of a critical supplier", "Défaillance d’un fournisseur critique"),
    ("F06.02", "F06", "Vendor or technology lock-in", "Verrouillage fournisseur ou technologique"),
    ("F06.03", "F06", "Insufficient reversibility or portability", "Réversibilité ou portabilité insuffisante"),
    ("F07.01", "F07", "Misalignment between business strategy and IS trajectory", "Désalignement entre la stratégie métier et la trajectoire du SI"),
    ("F07.02", "F07", "Economic unsustainability of the solution", "Insoutenabilité économique de la solution"),
    ("F08.01", "F08", "Lack of skills for design, delivery and operation", "Manque de compétences pour la conception, la livraison et l’exploitation"),
    ("F08.02", "F08", "Design or delivery not adapted to the business need", "Conception ou livraison inadaptée au besoin métier"),
    ("F08.03", "F08", "Non-adoption of the solution by users", "Non-adoption de la solution par les utilisateurs"),
    ("F08.04", "F08", "Drift in schedule, costs or delivery capacity", "Dérive du planning, des coûts ou de la capacité de livraison"),
    ("F08.05", "F08", "Incompatibility or blockage between interdependent initiatives", "Incompatibilité ou blocage entre initiatives interdépendantes"),
]

REFERENCE_VALUES = {
    "object_type": [
        ("APPLICATION", "Application", "Application"),
        ("TECHNOLOGY_COMPONENT", "Technology / Component", "Technologie / composant"),
        ("PLATFORM_INFRA", "Platform / Infra", "Plateforme / infrastructure"),
        ("DATA_INTEGRATION", "Data / Integration", "Données / intégration"),
        ("IT_BUSINESS_SERVICE", "Service IT / Business", "Service IT / métier"),
        ("PROVIDER_THIRD_PARTY", "Provider / Third Party", "Fournisseur / tiers"),
        ("ARCHI_DOMAIN_CAPABILITY", "Archi Domain / Capa", "Domaine d’architecture / capacité"),
        ("ENTERPRISE_IT_LANDSCAPE", "Enterprise / IT landscape", "Entreprise / paysage SI"),
        ("DATA_ENTITY", "Data entity", "Entité de données"),
        ("ARCHITECTURE_AREA", "Architecture area", "Domaine d’architecture"),
        ("BUSINESS_CAPABILITY", "Business capability", "Capacité métier"),
        ("BUSINESS_UNIT", "Business unit", "Unité métier"),
    ],
    "source_type": [
        ("ADR_EXCEPTION", "ADR / Exception", "ADR / exception"),
        ("ARB", "ARB", "ARB"),
        ("PROJECT", "Project", "Projet"),
        ("APP_TECH_LIFECYCLE_REVIEW", "App / Techno lifecycle review", "Revue du cycle de vie applicatif / technologique"),
        ("AUDIT_COMPLIANCE_REVIEW", "Audit / Compliance review", "Revue d’audit / conformité"),
        ("INCIDENT_PROBLEM_MGMT", "Incident / Problem mgt", "Gestion des incidents / problèmes"),
    ],
    "scope_type": [
        ("TEAM", "Team", "Équipe"),
        ("DOMAIN", "Domain", "Domaine"),
        ("CAPABILITY", "Capability", "Capacité"),
        ("COMPANY_ENTITY", "Company / Entity", "Société / entité"),
    ],
}

# The source catalogue stays in English; only the two explicitly supplied quality notes are recorded.
DEFINITIONS = [
    ("RISK_001", "Deviation from architectural standards and principles", "Possibility that a solution deviates from the standards, patterns or architectural principles defined by enterprise architecture, resulting in increased heterogeneity, complexity and maintenance costs of the information system.",
     ["Insufficient knowledge of standards and patterns.", "Strong project constraints.", "Unsuitable or obsolete standard or pattern.", "No compliant solution available.", "Insufficiently governed waiver."],
     ["Technological heterogeneity.", "Increased complexity.", "Higher maintenance costs.", "Integration difficulties.", "Technical debt."], []),
    ("RISK_002", "Gap between the approved architecture and the implemented solution", "Possibility that the solution actually implemented diverges from the approved architecture, resulting in the loss of expected architectural qualities and uncontrolled deviations in the information system.",
     ["Modification during delivery without renewed approval.", "Misunderstanding of the design.", "Insufficient documentation.", "Schedule pressure.", "Insufficient compliance checks."],
     ["Reduced architectural requirements.", "Undocumented deviations.", "Security, performance or resilience problems.", "Redesign.", "Maintenance difficulties."], []),
    ("RISK_003", "Implementing a solution without architectural validation", "Possibility that a solution is designed or implemented without the required architectural approvals, resulting in uncontrolled decisions and inconsistencies in the information system.",
     ["Bypassing the governance process.", "Project urgency.", "Poorly defined roles.", "Architecture involvement too late.", "Approval milestones missing from the delivery process."],
     ["Uncontrolled decisions.", "Non-compliance with standards.", "Unidentified technical risks.", "Inconsistency in the information system.", "Late and costly remediation."], []),
    ("RISK_004", "Accumulation of technical and architectural debt", "Possibility that technical and architectural debt accumulates in the information system, resulting in higher maintenance costs and reduced maintainability and ability to evolve.",
     ["Short-term trade-offs.", "Temporary workarounds becoming permanent.", "Refactoring postponed.", "Insufficient modernization budget."],
     ["Higher maintenance costs.", "Slower changes.", "Increased complexity.", "More frequent incidents.", "Reduced agility."], []),
    ("RISK_005", "Application functional overlap", "Possibility that several applications cover identical or similar functional needs, resulting in additional costs, operational confusion and increased complexity of the application landscape.",
     ["Lack of visibility of the application landscape.", "Siloed decisions.", "Local acquisitions.", "Insufficient portfolio governance."],
     ["Additional licensing and operating costs.", "User confusion.", "Landscape complexity.", "More interfaces."], []),
    ("RISK_006", "Incomplete or outdated knowledge of heritage", "Possibility that an evolution or transformation decision relies on incomplete or outdated knowledge of the IT landscape, resulting in duplicates, inconsistencies or unanticipated impacts.",
     ["Insufficient documentation.", "Unmaintained repositories.", "Poorly defined responsibilities.", "Information scattered across several tools."],
     ["Creation of duplicates and redundancies.", "Overlooked dependencies.", "Unanticipated impacts.", "Poor rationalization decisions.", "Additional costs."], []),
    ("RISK_007", "Systemic failure of the IS", "Possibility that a change or failure in one component propagates to other highly dependent components, resulting in cascading malfunctions or increased complexity of change.",
     ["Tight coupling.", "Numerous or undocumented dependencies.", "Critical shared components.", "Lack of isolation mechanisms."],
     ["Cascading incidents.", "Unavailability of several services.", "Difficulty evolving the information system.", "Longer resolution time."], []),
    ("RISK_008", "Proliferation of solutions outside IT governance", "Possibility that solutions are developed or acquired outside IT governance, resulting in security, compliance, integration, duplication and maintainability risks.",
     ["Unmet business needs.", "IT lead times that are too long.", "No solution catalogue.", "Insufficient controls."],
     ["Vulnerabilities.", "Non-compliance.", "Application duplication.", "Support difficulties.", "Hidden costs."], []),
    ("RISK_009", "Technological obsolescence", "Possibility that the technologies in use reach end of life or support, compromising the security, maintainability, availability or ability to evolve the information system.",
     ["Migration postponed.", "No lifecycle management.", "Dependencies on legacy technologies.", "Budget constraints.", "End of vendor support."],
     ["Vulnerabilities.", "Lack of support.", "Difficulty finding required skills.", "More incidents.", "Maintenance costs.", "Blocked changes."], []),
    ("RISK_010", "Insufficient governance of the application lifecycle", "Possibility that decisions to evolve, retain or retire an application are insufficiently controlled, resulting in late, inconsistent or uncontrolled decisions.",
     ["No business or IT owner.", "Unclear RACI.", "No periodic review.", "Insufficient portfolio management."],
     ["Unnecessary application retention.", "Late decisions.", "Obsolescence.", "Avoidable costs."], []),
    ("RISK_011", "Late detection of incidents and damage", "Possibility that an incident or service degradation is not detected early enough, prolonging the incident and increasing its impact on the service.",
     ["Incomplete monitoring.", "Insufficient alerts.", "Unusable logs.", "No SLO."],
     ["Longer incident duration.", "Higher MTTR.", "Increased business impact.", "Prolonged unavailability.", "Degraded user experience."], []),
    ("RISK_012", "Inability to maintain or restore service after a failure", "Possibility that a system cannot maintain or restore service and data to expected levels after a failure, resulting in prolonged unavailability or data loss.",
    ["Insufficient redundancy.", "« Incomplete » : élément incomplet à clarifier.", "Untested backups.", "Poorly defined RTO and RPO.", "Insufficient resilience testing.", "Application maintenance resources unavailable."],
     ["Prolonged interruption.", "Data loss.", "SLA non-compliance.", "Financial losses and reputational damage."], ["Incomplete"]),
    ("RISK_013", "Inability to absorb a surge", "Possibility that an application or infrastructure cannot absorb a significant increase in activity or data volumes, resulting in degraded performance or service levels.",
     ["Undersizing.", "Non-scalable architecture.", "No capacity planning.", "No load testing.", "Technical platform limits."],
     ["Performance degradation and saturation.", "Unavailability.", "Degraded user experience."], []),
    ("RISK_014", "Data quality and integrity", "Possibility that data used is incorrect, outdated, incomplete or duplicated, resulting in operational errors or decisions based on incorrect information.",
     ["Insufficient quality controls.", "Multiple uncontrolled sources.", "Inconsistent reference data.", "No data owner."],
    ["Operational errors.", "Incorrect decisions.", "Unreliable reporting.", "Manual corrections.", "Risque réglementaire à confirmer, mention TBC."], ["Risque réglementaire à confirmer, mention TBC."]),
    ("RISK_015", "Failure of inter-application exchanges", "Possibility that exchanges between applications become unavailable, unstable or incorrect, compromising the availability and reliability of exchanged information.",
     ["Fragile interfaces.", "Uncontrolled architecture change.", "Dependency on a critical API or network."],
     ["Unavailable or inconsistent data.", "Process interruption.", "Lost transactions.", "Manual reconciliation."], []),
    ("RISK_016", "Data protection non-compliance", "Possibility that a solution collects, processes, stores or transfers personal data contrary to applicable regulatory requirements, resulting in sanctions, reputational damage or restrictions on use of the solution.",
     ["Excessive data collection.", "Non-compliant location or transfer.", "Lack of knowledge of the regulatory framework.", "Insufficient audit or internal audit."],
     ["Sanctions.", "Reputational damage.", "Restriction or suspension of processing.", "Remediation costs.", "Impact on the service."], []),
    ("RISK_017", "Compromise of systems or data", "Possibility that a design weakness or security mechanisms enable unauthorized access, modification or interruption of systems or data, resulting in harm to the confidentiality, integrity or availability of the information system.",
     ["Security insufficiently considered from design.", "Insufficient segmentation.", "Weak access controls.", "Vulnerabilities."],
     ["Data leakage or alteration.", "Service interruption.", "Fraud.", "Reputational damage."], []),
    ("RISK_018", "Insufficient control of sovereignty", "Possibility that the location, hosting or dependency on suppliers and technologies subject to external jurisdictions reduces the company's control over its data, services or infrastructure, resulting in constraints on access, reversibility, continuity or evolution.",
     ["Data or services hosted in external jurisdictions.", "Dependency on a non-European supplier.", "Use of proprietary technologies.", "No alternative or fallback solution.", "Insufficient control of subcontractors and their dependency chain."],
     ["Loss of control over data or services.", "Exposure to decisions or requirements from external jurisdictions.", "Service interruption or degradation.", "Significant migration or remediation costs."], []),
    ("RISK_019", "Failure of a critical supplier", "Possibility that a critical supplier can no longer provide, maintain or support a service on which the information system depends, resulting in service interruption, degraded operations or inability to evolve the solution.",
     ["Supplier bankruptcy.", "Operational inability.", "Insufficient service quality.", "Strong dependency on a single supplier.", "Supplier discontinues an offering."],
     ["Service interruption.", "Loss of support.", "Emergency migration.", "Additional costs.", "Business impact."], []),
    ("RISK_020", "Vendor or technology lock-in", "Possibility that a solution becomes highly dependent on a supplier, technology or platform that is difficult to replace, limiting the ability to negotiate, evolve or change the solution.",
     ["Proprietary technologies.", "Closed APIs.", "Lack of open standards.", "Skills concentrated at one supplier."],
     ["Higher costs.", "Dependency on the supplier roadmap.", "Migration difficulties.", "Loss of negotiating power."], []),
    ("RISK_021", "Insufficient reversibility or portability", "Possibility that a solution, its data or its components cannot be transferred or replaced under acceptable conditions, resulting in significant costs, delays or interruptions when changing supplier or technology.",
     ["No exit strategy.", "Proprietary formats.", "Insufficient documentation.", "Strong dependencies.", "No reversibility testing."],
     ["Long or impossible migration.", "Service interruption.", "Additional costs.", "Forced retention of a technology or supplier."], []),
    ("RISK_022", "Misalignment between business strategy and IS trajectory", "Possibility that information system directions and investments diverge from business priorities, resulting in low-value investments or inability of the information system to support the strategy.",
     ["Insufficient business and IT governance.", "Unstable business priorities.", "Poor strategic visibility.", "Information system roadmap not updated."],
     ["Low-value investments.", "Unsupported business capabilities.", "Duplicated investments.", "Strategic delay.", "Unsuitable technology trajectory."], []),
    ("RISK_023", "Economic unsustainability of the solution", "Possibility that the delivery, operating, licensing or change costs of a solution become incompatible with the value delivered or the organization's budget capacity, calling its sustainability into question.",
     ["Total cost of ownership (TCO) poorly assessed.", "Variable cloud costs.", "Increasing license costs.", "Oversized architecture.", "High integration or support costs."],
     ["Budget overrun.", "Scope reduction.", "Reduced return on investment (ROI)."], []),
    ("RISK_024", "Lack of skills for design, delivery and operation", "Possibility that teams do not have the skills or knowledge needed to properly design, deliver or operate a solution, resulting in design errors, delays, degraded quality or operational difficulties.",
     ["Staff turnover.", "Skills scarcity.", "Insufficient training.", "Dependency on a few experts.", "Niche technology.", "Insufficient knowledge transfer."],
     ["Design errors.", "Delays.", "Degraded quality.", "Operational incidents.", "Maintenance difficulties.", "Supplier dependency."], []),
    ("RISK_025", "Design or delivery not adapted to the business need", "Possibility that a designed or delivered solution does not properly meet expected business needs, resulting in redesign, delays, additional costs or reduced delivered value.",
     ["Unclear or unstable need.", "Low business involvement.", "Insufficient discovery phase.", "Poorly formalized requirements.", "Insufficient validation by the client or requester."],
     ["Redesign.", "Delays.", "Additional costs.", "Low business value.", "User workarounds.", "Dissatisfaction."], []),
    ("RISK_026", "Non-adoption of the solution by users", "Possibility that an implemented solution is insufficiently adopted by users, resulting in underuse, reduced expected benefits or continued alternative practices.",
     ["Insufficient change support.", "Insufficient training.", "Unsuitable user experience.", "No sponsorship.", "Insufficient integration into business practices."],
     ["Underuse.", "Benefits not realized.", "Parallel tools.", "Reduced productivity."], []),
    ("RISK_027", "Drift in schedule, costs or delivery capacity", "Possibility that a project cannot meet its planned deadlines, budget or resources, resulting in delays, additional costs, reduced scope or degraded delivery quality.",
     ["Effort underestimated.", "Insufficient resources.", "External dependencies.", "Technical uncertainties.", "Unrealistic planning."],
     ["Delays.", "Budget overrun.", "Reduction of initial scope.", "Lower quality.", "Expected benefits postponed."], []),
    ("RISK_028", "Incompatibility or blockage between interdependent initiatives", "Possibility that interdependent projects or initiatives evolve without coordination, resulting in incompatibilities, blockages, uncontrolled dependencies or delivery delays.",
     ["Uncoordinated roadmaps.", "Siloed decisions.", "Inconsistent sequencing."],
     ["Delivery blockage.", "Technical incompatibilities.", "Redesign.", "Cascading delays.", "Additional costs."], []),
]


def ensure_risk_catalog(db: Session) -> None:
    families = {item.id: item for item in db.scalars(select(RiskTaxonomyFamily)).all()}
    for family_id, name_en, name_fr in FAMILIES:
        if family_id not in families:
            db.add(RiskTaxonomyFamily(id=family_id, name_en=name_en, name_fr=name_fr))
    db.flush()

    existing_types = set(db.scalars(select(RiskTaxonomyType.id)).all())
    for type_id, family_id, label_en, label_fr in TYPES:
        if type_id not in existing_types:
            db.add(RiskTaxonomyType(id=type_id, family_id=family_id, label_en=label_en, label_fr=label_fr))
    db.flush()

    existing_codes = set(db.scalars(select(RiskHelpDefinition.risk_code)).all())
    for index, (code, title, description, causes, impacts, notes) in enumerate(DEFINITIONS, start=1):
        if code in existing_codes:
            continue
        type_id, _, _, title_fr = TYPES[index - 1]
        db.add(RiskHelpDefinition(
            id=f"RDEF_{index:03d}", risk_code=code, risk_number=index, subfamily_id=type_id,
            title_en=title, title_fr=title_fr, description_en=description,
            causes=causes, impacts=impacts, data_quality_notes=notes,
        ))
    db.flush()


def ensure_risk_reference_values(db: Session) -> None:
    existing = {(item.category, item.code) for item in db.scalars(select(RiskReferenceValue)).all()}
    for category, values in REFERENCE_VALUES.items():
        for code, label_en, label_fr in values:
            if (category, code) not in existing:
                db.add(RiskReferenceValue(id=f"{category.upper()}_{code}", category=category, code=code, label_en=label_en, label_fr=label_fr, is_active=True))
    db.flush()