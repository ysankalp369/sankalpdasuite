"""Project data schema – the single registry of every fact a Development Agreement needs.

Each field in a project's master database is stored as
    {"value": <any>, "status": <STATUS>, "sources": [{"doc_id","doc","page","para","snippet"}], "note": str}

Statuses (Module 5 distinctions):
    confirmed      – verified by a user (or single consistent extracted source accepted by a user)
    extracted      – found in an uploaded document, not yet verified
    verify         – information requiring verification (e.g. a single weak source, OCR text)
    conflict       – contradictory values found in different documents (never auto-resolved)
    missing        – not found anywhere
    na             – not applicable to this project
"""
from __future__ import annotations

from dataclasses import dataclass, field

STATUSES = ["confirmed", "extracted", "verify", "conflict", "missing", "na"]


@dataclass
class F:
    key: str
    label: str
    group: str
    type: str = "text"   # text|date|int|number|money|area_sqm|area_sqft|percent|months|years|list|longtext
    critical: bool = False
    category: str = "legal"  # legal | technical | commercial | member
    help: str = ""
    default: object = None   # a *drafting* default (policy), never a project fact
    choices: list[str] = field(default_factory=list)


FIELDS: list[F] = [
    # ---------------------------------------------------------------- society
    F("society.name", "Society name", "Society", critical=True),
    F("society.reg_no", "Registration number", "Society", critical=True),
    F("society.reg_date", "Registration date", "Society", "date", critical=True),
    F("society.pan", "Society PAN", "Society"),
    F("society.address", "Registered address", "Society", "longtext", critical=True),
    F("society.email", "Society email for notices", "Society"),
    F("society.chairman", "Chairman", "Society", critical=True),
    F("society.secretary", "Secretary", "Society", critical=True),
    F("society.treasurer", "Treasurer", "Society"),
    F("society.sgbm_redevelopment_date", "SGBM date – decision to redevelop", "Society", "date", critical=True),
    F("society.sgbm_pmc_date", "SGBM / MC date – PMC appointment", "Society", "date"),
    F("society.tender_notice_date", "Tender notice date", "Society", "date"),
    F("society.bidders_count", "Number of bids received", "Society", "int"),
    F("society.sgbm_selection_date", "SGBM date – developer selection (79A)", "Society", "date", critical=True),
    F("society.sgbm_selection_present", "Members present at selection SGBM", "Society", "int"),
    F("society.sgbm_selection_quorum_of", "Total members eligible at selection SGBM", "Society", "int"),
    F("society.authorised_officer", "Authorised officer of Deputy Registrar present", "Society"),
    F("society.order_79a_date", "Deputy Registrar 79A order / NOC date", "Society", "date", critical=True),
    F("society.registrar_office", "Office of the Deputy Registrar", "Society"),
    F("society.sgbm_da_approval_date", "SGBM date – approval of draft DA", "Society", "date", critical=True),
    F("society.appointment_letter_date", "Developer appointment letter date", "Society", "date", critical=True),
    F("society.acceptance_letter_date", "Developer acceptance letter date", "Society", "date"),
    F("society.consents_received", "Number of written member consents", "Society", "int"),

    # ---------------------------------------------------------------- PMC & advisor
    F("pmc.name", "PMC name", "Consultants", critical=True),
    F("pmc.address", "PMC address", "Consultants", "longtext"),
    F("pmc.appointment_date", "PMC appointment date", "Consultants", "date"),
    F("legal.name", "Legal advisor", "Consultants", critical=True),
    F("legal.address", "Legal advisor address", "Consultants", "longtext"),
    F("legal.appointment_date", "Legal advisor appointment date", "Consultants", "date"),

    # ---------------------------------------------------------------- property
    F("property.plot_no", "Plot number", "Property", critical=True),
    F("property.sector", "Sector", "Property", critical=True),
    F("property.node", "Node / village", "Property", critical=True),
    F("property.city", "City / taluka / district", "Property", default="Navi Mumbai"),
    F("property.pincode", "PIN code", "Property"),
    F("property.plot_area_sqm", "Plot area (sq. m.)", "Property", "area_sqm", critical=True, category="technical"),
    F("property.authority", "Planning authority", "Property", choices=["NMMC", "Panvel Municipal Corporation", "CIDCO"], critical=True),
    F("property.lessor", "Lessor", "Property", default="City and Industrial Development Corporation of Maharashtra Limited (CIDCO)"),
    F("property.lease_deed_date", "Lease Deed date", "Property", "date", critical=True),
    F("property.lease_reg_no", "Lease Deed registration number", "Property", critical=True),
    F("property.lease_sro", "Sub-Registrar office", "Property"),
    F("property.lease_term_years", "Lease term (years)", "Property", "int"),
    F("property.lease_commencement", "Lease commencement date", "Property", "date"),
    F("property.atl_date", "Agreement to Lease date", "Property", "date"),
    F("property.cidco_noc_status", "CIDCO redevelopment NOC status", "Property"),
    F("property.boundary_north", "Boundary – North", "Property", critical=True),
    F("property.boundary_south", "Boundary – South", "Property", critical=True),
    F("property.boundary_east", "Boundary – East", "Property", critical=True),
    F("property.boundary_west", "Boundary – West", "Property", critical=True),
    F("property.zone", "Zoning", "Property", default="Residential"),
    F("property.existing_buildings", "Existing buildings description", "Property", "longtext", critical=True, category="technical"),
    F("property.existing_bua_sqm", "Existing built-up area (sq. m.)", "Property", "area_sqm", category="technical"),
    F("property.construction_year", "Year of construction", "Property", "int"),
    F("property.structural_audit", "Structural audit report (date / conclusion)", "Property", "longtext", category="technical"),
    F("property.units_count", "Number of existing units", "Property", "int", critical=True, category="member"),
    F("property.members_count", "Number of registered members", "Property", "int", critical=True, category="member"),
    F("property.existing_carpet_total_sqm", "Aggregate existing RERA carpet area (sq. m.)", "Property", "area_sqm", category="technical"),
    F("property.litigation", "Litigation disclosures", "Property", "longtext"),
    F("property.encumbrances", "Mortgages / encumbrances on plot", "Property", "longtext"),
    F("property.cidco_dues", "CIDCO / municipal dues outstanding", "Property", "longtext", category="commercial"),

    # ---------------------------------------------------------------- developer
    F("developer.name", "Developer name", "Developer", critical=True),
    F("developer.constitution", "Constitution", "Developer", choices=["private limited company", "public limited company", "limited liability partnership", "partnership firm", "proprietary concern"], critical=True),
    F("developer.incorporation_law", "Incorporated under", "Developer", default="the Companies Act, 2013"),
    F("developer.cin", "CIN / LLPIN / firm reg. no.", "Developer", critical=True),
    F("developer.pan", "Developer PAN", "Developer", critical=True),
    F("developer.gstin", "Developer GSTIN", "Developer"),
    F("developer.address", "Developer registered office", "Developer", "longtext", critical=True),
    F("developer.email", "Developer email for notices", "Developer"),
    F("developer.signatories", "Authorised signatories", "Developer", critical=True),
    F("developer.board_resolution_date", "Board resolution date", "Developer", "date", critical=True),
    F("developer.offer_date", "Accepted final offer date", "Developer", "date", critical=True),
    F("developer.net_worth", "Net worth (as certified)", "Developer", "money", category="commercial"),
    F("developer.turnover", "Turnover (as certified)", "Developer", "money", category="commercial"),
    F("developer.guarantor", "Personal / corporate guarantor", "Developer"),
    F("developer.rera_projects", "RERA-registered projects (disclosed)", "Developer", "longtext"),
    F("developer.litigation", "Developer litigation disclosure", "Developer", "longtext"),
    F("developer.insolvency", "Insolvency disclosure", "Developer", "longtext"),

    # ---------------------------------------------------------------- technical / FSI
    F("tech.basic_fsi", "Basic FSI (ratio)", "Technical", "number", category="technical"),
    F("tech.total_potential_sqm", "Full Development Potential (sq. m.)", "Technical", "area_sqm", category="technical"),
    F("tech.rehab_carpet_total_sqft", "Total rehabilitation carpet area (sq. ft. RERA)", "Technical", "area_sqft", critical=True, category="technical"),
    F("tech.sale_carpet_total_sqft", "Developer free-sale carpet area (sq. ft.)", "Technical", "area_sqft", category="technical"),
    F("tech.building_config", "Proposed building configuration", "Technical", category="technical"),
    F("tech.additional_area_percent", "Additional free area over existing (%)", "Technical", "percent", category="technical"),
    F("tech.parking_per_unit", "Parking spaces per existing unit", "Technical", "int", category="technical"),
    F("tech.amenities", "Common amenities (list)", "Technical", "list", category="technical"),
    F("tech.specifications", "Flat specifications (list)", "Technical", "list", category="technical"),
    F("tech.architect", "Project architect", "Technical"),
    F("tech.excess_area_rate", "Rate for additional area purchase by members", "Technical", "money", category="commercial"),
    F("tech.measurement_tolerance_percent", "Permitted carpet area shortfall tolerance (%)", "Technical", "percent", default=0, category="technical"),

    # ---------------------------------------------------------------- commercial terms
    F("comm.rent_basis", "Rent basis", "Commercial", choices=["per unit (uniform)", "per sq. ft. of existing carpet", "member-wise schedule"], critical=True, category="commercial"),
    F("comm.rent_monthly", "Monthly rent per unit (uniform)", "Commercial", "money", category="commercial"),
    F("comm.rent_per_sqft", "Monthly rent per sq. ft. existing carpet", "Commercial", "money", category="commercial"),
    F("comm.rent_escalation_percent", "Rent escalation (%)", "Commercial", "percent", critical=True, category="commercial"),
    F("comm.rent_escalation_months", "Escalation interval (months)", "Commercial", "months", critical=True, category="commercial"),
    F("comm.rent_advance_months", "Rent paid in advance (months)", "Commercial", "months", category="commercial"),
    F("comm.rent_due_day", "Monthly rent due by (day of month)", "Commercial", "int", default=5, category="commercial"),
    F("comm.brokerage", "Brokerage per unit", "Commercial", "money", critical=True, category="commercial"),
    F("comm.deposit", "Refundable security deposit per unit", "Commercial", "money", category="commercial"),
    F("comm.shifting", "Shifting charges per unit", "Commercial", "money", critical=True, category="commercial"),
    F("comm.reshifting", "Re-shifting charges per unit", "Commercial", "money", critical=True, category="commercial"),
    F("comm.corpus", "Corpus fund per unit", "Commercial", "money", critical=True, category="commercial"),
    F("comm.corpus_new_member", "Corpus contribution per new (free-sale) member", "Commercial", "money", category="commercial"),
    F("comm.hardship", "Hardship compensation per unit", "Commercial", "money", category="commercial"),
    F("comm.society_office_rent", "Temporary society office rent (monthly)", "Commercial", "money", category="commercial"),
    F("comm.additional_benefits", "Additional benefits", "Commercial", "longtext", category="commercial"),
    F("comm.delay_interest_percent", "Interest on delayed payments (% p.a.)", "Commercial", "percent", default=18, category="commercial"),
    F("comm.payment_grace_days", "Grace for rent payment (days)", "Commercial", "int", default=7, category="commercial"),

    # ---------------------------------------------------------------- security
    F("security.bg_amount", "Bank Guarantee amount", "Security", "money", critical=True, category="commercial"),
    F("security.bg_milestones", "BG release milestones", "Security", "list", category="commercial",
      help="List of {milestone, amount}. Must total the BG amount; a tranche must be retained through DLP."),
    F("security.additional", "Additional security (flats in lien / guarantee)", "Security", "longtext", category="commercial"),
    F("security.ld_per_month", "Liquidated damages per month of delay", "Security", "money", critical=True, category="commercial"),
    F("security.dlp_retention", "BG retained during DLP", "Security", "money", category="commercial"),

    # ---------------------------------------------------------------- timelines
    F("time.approval_months", "Period to obtain Initial Approvals (months)", "Timeline", "months", critical=True),
    F("time.vacation_notice_days", "Vacation period after Vacation Notice (days)", "Timeline", "int", default=30),
    F("time.construction_months", "Construction period to Full OC (months)", "Timeline", "months", critical=True),
    F("time.grace_months", "Grace period (months)", "Timeline", "months", critical=True),
    F("time.longstop_months", "Long-stop date after Completion Date (months)", "Timeline", "months", default=6),
    F("time.dlp_years", "Defect Liability Period (years)", "Timeline", "years", default=5),
    F("time.cure_days", "Cure period for Developer default (days)", "Timeline", "int", default=60),
    F("time.paaa_days", "Period to register PAAAs after Registration Notice (days)", "Timeline", "int", default=30),
    F("time.possession_take_days", "Period for members to take possession (days)", "Timeline", "int", default=30),
    F("time.lease_amendment_months", "Period after Full OC to obtain CIDCO lease amendment (months)", "Timeline", "months", default=12),

    # ---------------------------------------------------------------- execution
    F("exec.place", "Place of execution", "Execution", default="Navi Mumbai"),
    F("exec.date", "Date of execution", "Execution", "date"),
    F("exec.arbitration_seat", "Seat of arbitration", "Execution", default="Navi Mumbai"),
    F("exec.courts", "Courts with jurisdiction", "Execution", default="the competent courts at Navi Mumbai / Thane"),
]

FIELD_MAP = {f.key: f for f in FIELDS}
GROUPS = list(dict.fromkeys(f.group for f in FIELDS))


def empty_entry(f: F) -> dict:
    if f.default is not None:
        return {"value": f.default, "status": "confirmed", "sources": [], "note": "Drafting default (firm policy) – change if negotiated otherwise."}
    return {"value": None, "status": "missing", "sources": [], "note": ""}


def initial_data() -> dict:
    return {f.key: empty_entry(f) for f in FIELDS}


def value(data: dict, key: str, fallback=None):
    e = data.get(key) or {}
    v = e.get("value")
    if e.get("status") in ("missing", "conflict") or v in (None, "", []):
        return fallback
    return v
