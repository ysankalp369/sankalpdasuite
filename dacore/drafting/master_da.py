"""MASTER DEVELOPMENT AGREEMENT – consolidated, society-protective drafting framework.

Structure follows the Preetisangam registered agreement (recitals → definitions →
purpose → grant → entitlement → consideration → developer rights → representations →
obligations → completion → termination → miscellaneous → schedules), re-ordered into the
23-Article master structure and strengthened where the reference agreements were weak.

Placeholder syntax resolved by render.py:
    {{key}}            value of a project field (e.g. {{society.name}})
    {{money:key}}      Rs. 25,000/- (Rupees Twenty-Five Thousand Only)
    {{num:key}}        36 (Thirty-Six)
    {{date:key}}       12th April, 2026
    {{upper:key}}      upper-cased value
    [[ref:clause_id]]  cross-reference, rendered as "Clause 6.3"
    [[art:clause_id]]  rendered as "Article VI"
    [[sch:key]]        schedule reference, rendered as "the Third Schedule"
    [[ann:key]]        annexure reference, rendered as "Annexure F"
NO project facts are hard-coded in this file.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class L:  # clause-library metadata
    subject: str
    classification: str = "Preferred"        # Preferred | Acceptable alternative | Negotiable | Not recommended | Critical Society protection
    risk: str = ""
    provision: str = ""
    explain: str = ""
    neutral: str = ""


@dataclass
class C:
    id: str
    text: str
    sub: list["C"] = field(default_factory=list)
    when: str | None = None
    lib: L | None = None
    h: str | None = None          # bold lead-in heading


def c(id, text, *sub, when=None, lib=None, h=None):
    return C(id, text, list(sub), when, lib, h)


@dataclass
class Article:
    num: str
    title: str
    clauses: list[C]
    intro: str = ""


@dataclass
class Definition:
    term: str
    text: str
    when: str | None = None


# --------------------------------------------------------------------------------------------
PARTIES = [
    ("SOCIETY",
     "{{upper:society.name}}, a co-operative housing society registered under the provisions of the "
     "Maharashtra Co-operative Societies Act, 1960 bearing Registration No. {{society.reg_no}} dated "
     "{{date:society.reg_date}}, having PAN {{society.pan}} and its registered office at {{society.address}}, "
     "acting through its duly authorised office-bearers, namely {{society.chairman}} (Chairman), "
     "{{society.secretary}} (Secretary) and {{society.treasurer}} (Treasurer), authorised vide resolution of the "
     "Special General Body Meeting held on {{date:society.sgbm_da_approval_date}}, a copy whereof is annexed hereto as "
     "[[ann:sgbm_resolution]], hereinafter referred to as the “Society” (which expression shall, unless it be "
     "repugnant to the context or meaning thereof, be deemed to mean and include its successors and permitted assigns) "
     "of the FIRST PART;"),
    ("DEVELOPER",
     "{{upper:developer.name}}, a {{developer.constitution}} incorporated / constituted under {{developer.incorporation_law}} "
     "bearing CIN / registration No. {{developer.cin}}, having PAN {{developer.pan}} and GSTIN {{developer.gstin}}, and "
     "having its registered office at {{developer.address}}, acting through its authorised signatory/ies "
     "{{developer.signatories}}, duly authorised vide resolution dated {{date:developer.board_resolution_date}}, a copy "
     "whereof is annexed hereto as [[ann:board_resolution]], hereinafter referred to as the “Developer” (which expression "
     "shall, unless it be repugnant to the context or meaning thereof, be deemed to mean and include its successors and "
     "permitted assigns only, and shall not include any assignee or transferee save as expressly permitted under "
     "[[ref:assign_bar]]) of the SECOND PART;"),
    ("EXISTING MEMBERS",
     "THE EXISTING MEMBERS of the Society whose names, Existing Premises and entitlements are set out in "
     "[[sch:members]], each of whom shall execute this Agreement or a Deed of Confirmation in the form approved by "
     "the Society, hereinafter collectively referred to as the “Existing Members” and individually as an “Existing "
     "Member” (which expression shall, unless repugnant to the context or meaning thereof, be deemed to mean and include "
     "their respective heirs, executors, administrators and permitted assigns) of the THIRD PART, as Confirming Parties."),
]

RECITALS = [
    c("rec.cidco",
      "{{property.lessor}} (“CIDCO”) is the New Town Development Authority declared under Section 113 of the "
      "Maharashtra Regional and Town Planning Act, 1966 for the area designated as the site for the new town of Navi "
      "Mumbai, and the lands within such area have been acquired by the State Government and vested in CIDCO for "
      "development and disposal."),
    c("rec.plot",
      "CIDCO is the owner of all that piece and parcel of land bearing Plot No. {{property.plot_no}}, Sector "
      "{{property.sector}}, {{property.node}}, {{property.city}} admeasuring {{property.plot_area_sqm}} square metres "
      "or thereabouts, lying within the limits of {{property.authority}}, more particularly described in "
      "[[sch:property]] (the “Plot”)."),
    c("rec.buildings",
      "CIDCO constructed on the Plot {{property.existing_buildings}} (the “Existing Buildings”) comprising "
      "{{num:property.units_count}} units (the “Existing Premises”), more particularly described in [[sch:existing]]. "
      "The Plot, the Existing Buildings and the Existing Premises are hereinafter collectively referred to as the "
      "“Property”."),
    c("rec.society",
      "The allottees of the Existing Premises formed themselves into the Society, which was registered under the "
      "Maharashtra Co-operative Societies Act, 1960 bearing Registration No. {{society.reg_no}} dated "
      "{{date:society.reg_date}}. A copy of the certificate of registration is annexed hereto as [[ann:reg_cert]]."),
    c("rec.lease",
      "By a Lease Deed dated {{date:property.lease_deed_date}} registered with the office of the Sub-Registrar of "
      "Assurances at {{property.lease_sro}} under Serial No. {{property.lease_reg_no}}, CIDCO demised the Plot together "
      "with the Existing Buildings unto the Society for a term of {{property.lease_term_years}} years commencing from "
      "{{date:property.lease_commencement}} on the terms and conditions contained therein (the “Lease Deed”)."),
    c("rec.members",
      "As on the date hereof the Society comprises {{num:property.units_count}} Existing Premises held by "
      "{{num:property.members_count}} registered members. The Parties expressly record that the number of units and the "
      "number of registered members are distinct: certain members hold more than one unit, certain units are held "
      "jointly, and the transmission or transfer of certain units is pending, as set out in [[sch:members]] and "
      "[[sch:disclosures]]. The Existing Members collectively hold an aggregate carpet area of "
      "{{property.existing_carpet_total_sqm}} square metres (RERA carpet area) or thereabouts."),
    c("rec.dilapidated",
      "The Existing Buildings are old and require redevelopment, as recorded in the structural audit "
      "{{property.structural_audit}}. At its Special General Body Meeting held on "
      "{{date:society.sgbm_redevelopment_date}}, the Society resolved to undertake redevelopment of the Property in "
      "accordance with the directions issued by the State Government under Section 79A of the Maharashtra Co-operative "
      "Societies Act, 1960 (the “79A Directions”)."),
    c("rec.pmc",
      "The Society appointed {{pmc.name}} of {{pmc.address}} as its Project Management Consultant (the “PMC”) and "
      "{{legal.name}} of {{legal.address}} as its legal advisor (the “Legal Advisor”), to advise and assist the Society "
      "in the redevelopment of the Property, including after the execution of this Agreement until completion of the "
      "Project."),
    c("rec.tender",
      "Pursuant to a tender notice dated {{date:society.tender_notice_date}}, the Society invited offers from developers "
      "for the redevelopment of the Property. {{num:society.bidders_count}} offers were received and evaluated by the PMC, "
      "which submitted its comparative technical and financial evaluation report to the Society."),
    c("rec.selection",
      "At the Special General Body Meeting held on {{date:society.sgbm_selection_date}} in the presence of "
      "{{society.authorised_officer}}, the authorised officer of the {{society.registrar_office}}, and attended by "
      "{{society.sgbm_selection_present}} members out of {{society.sgbm_selection_quorum_of}} members, the Society "
      "selected the Developer for the redevelopment of the Property on the basis of its accepted final offer dated "
      "{{date:developer.offer_date}} (the “Accepted Offer”), a copy whereof is annexed hereto as [[ann:offer]]."),
    c("rec.79a",
      "By order dated {{date:society.order_79a_date}}, the {{society.registrar_office}} recorded the selection of the "
      "Developer in accordance with the 79A Directions, a copy whereof is annexed hereto as [[ann:order79a]]."),
    c("rec.appointment",
      "By letter dated {{date:society.appointment_letter_date}}, the Society appointed the Developer, and the Developer "
      "accepted such appointment by letter dated {{date:society.acceptance_letter_date}}, subject to the execution of this "
      "Agreement."),
    c("rec.da_approval",
      "The draft of this Agreement and the draft of the Power of Attorney were placed before and approved by the "
      "members of the Society at the Special General Body Meeting held on {{date:society.sgbm_da_approval_date}}, which "
      "also authorised the office-bearers named hereinabove to execute and register this Agreement and the said Power "
      "of Attorney on behalf of the Society."),
    c("rec.guarantor", "{{developer.guarantor}} has agreed to furnish a deed of guarantee and undertaking in favour of "
      "the Society securing the due performance of the Developer’s obligations under this Agreement.",
      when="developer.guarantor"),
    c("rec.record", "The Parties are desirous of recording the terms and conditions agreed between them in writing, as "
      "hereinafter appearing."),
]

# --------------------------------------------------------------------------------------------
DEFINITIONS = [
    Definition("79A Directions", "means the directions issued by the Government of Maharashtra under Section 79A of the MCS Act governing redevelopment of co-operative housing societies, as amended, modified or substituted from time to time."),
    Definition("Accepted Offer", "has the meaning ascribed to it in the Recitals, and includes all clarifications, revisions and improvements thereto accepted in writing by the Society, which shall form part of this Agreement; provided that where the Accepted Offer is more beneficial to the Society or the Existing Members than this Agreement, the Accepted Offer shall prevail."),
    Definition("Agreement", "means this Development Agreement together with its Recitals, Schedules and Annexures, as amended in writing in accordance with [[ref:amend]]."),
    Definition("Applicable Laws", "means all statutes, enactments, ordinances, rules, regulations, notifications, bye-laws, development control regulations (including the UDCPR), directions, policies, guidelines, circulars, orders, judgments and decrees of any Authority having the force of law, as in force from time to time."),
    Definition("Approvals", "means all approvals, sanctions, permissions, no-objection certificates, licences, clearances, intimations of disapproval, development permissions, commencement certificates, occupation certificates and other consents of any Authority required for the redevelopment of the Property and the completion of the Project in accordance with this Agreement."),
    Definition("Authority", "means CIDCO, {{property.authority}}, the Maharashtra Real Estate Regulatory Authority, the Deputy Registrar of Co-operative Societies and every other governmental, statutory, municipal or local authority, body or tribunal having jurisdiction over the Property, the Project or the Parties."),
    Definition("Bank Guarantee", "means the unconditional, irrevocable and on-demand guarantee of a scheduled commercial bank to be furnished by the Developer in favour of the Society in terms of [[art:bg]] and in the format set out in [[ann:bg_format]]."),
    Definition("Commencement Certificate", "means the certificate issued by {{property.authority}} under the Maharashtra Regional and Town Planning Act, 1966 permitting commencement of the construction of the New Building on the Plot up to the full height of the New Building as per the sanctioned plans, or where the Authority issues it in parts, such certificate covering at least the entire Rehabilitation Component."),
    Definition("Commencement Date", "means the date on which the Developer actually commences construction of the New Building on the Plot after the Handover Date."),
    Definition("Completion Date", "has the meaning ascribed to it in [[ref:completion_date]]."),
    Definition("Construction Period", "means the period commencing on the Handover Date and ending on the Completion Date."),
    Definition("Corpus Fund", "means the non-refundable corpus amount payable by the Developer to the Society in terms of [[ref:corpus]], which shall be the absolute property of the Society."),
    Definition("Defect Liability Period", "means the period of {{num:time.dlp_years}} years from the Possession Date or such longer period as may be prescribed under Applicable Laws, including Section 14(3) of RERA."),
    Definition("Developer’s Free Sale Component", "means the premises, parking spaces and other areas in the New Building, other than the Rehabilitation Component and the Common Areas and Amenities, which the Developer is entitled to sell in terms of [[art:free_sale]]."),
    Definition("Development Potential", "means the entire floor space index and development potential available or which may become available in respect of the Plot under Applicable Laws, including basic FSI, premium FSI, ancillary FSI, incentive FSI, fungible FSI, TDR, road-widening and setback benefits, reservation benefits and Future FSI."),
    Definition("Existing Buildings", "has the meaning ascribed to it in the Recitals."),
    Definition("Existing Members", "means the persons whose names are recorded as members of the Society in respect of the Existing Premises, as set out in [[sch:members]], and includes their heirs, legal representatives and transferees admitted as members in accordance with this Agreement and the bye-laws of the Society."),
    Definition("Existing Premises", "means the {{num:property.units_count}} flats, shops and other units in the Existing Buildings, particulars whereof are set out in [[sch:members]]."),
    Definition("Force Majeure", "has the meaning ascribed to it in [[ref:fm_def]]."),
    Definition("Full Occupation Certificate", "means the occupation certificate issued by {{property.authority}} in respect of the whole of the New Building (and not a part occupation certificate), certifying that the New Building has been completed in accordance with the sanctioned plans, together with the fire-safety completion certificate / no-objection certificate and all other certificates required for lawful occupation of the Members’ New Premises."),
    Definition("Future FSI", "means any floor space index, TDR, incentive or other development potential which becomes available in respect of the Plot after the date of the Commencement Certificate, by reason of any change in Applicable Laws, policy, amalgamation or otherwise."),
    Definition("Handover Date", "means the date on which the Society delivers vacant possession of the Property to the Developer in accordance with [[ref:handover]], as recorded in the handover memorandum signed by the Society, the PMC and the Developer."),
    Definition("Initial Approvals", "means (i) the no-objection certificate of CIDCO for redevelopment of the Property; (ii) the sanction of building plans of the New Building by {{property.authority}} utilising the Development Potential in a manner consistent with this Agreement; and (iii) the Commencement Certificate."),
    Definition("Long-Stop Date", "means the date falling {{num:time.longstop_months}} months after the Completion Date."),
    Definition("Members’ New Premises", "means, collectively, the new flats/units to be constructed and allotted free of cost to the Existing Members in the New Building in terms of [[art:entitlement]] and [[sch:members]], together with the parking spaces and other entitlements attached thereto."),
    Definition("MCS Act", "means the Maharashtra Co-operative Societies Act, 1960 and the Maharashtra Co-operative Societies Rules, 1961, as amended from time to time."),
    Definition("New Building", "means the new building(s) to be constructed by the Developer on the Plot in accordance with the sanctioned plans and this Agreement, comprising the Rehabilitation Component, the Developer’s Free Sale Component and the Common Areas and Amenities."),
    Definition("Common Areas and Amenities", "means the common areas, facilities and amenities of the New Building described in [[sch:amenities]], all of which shall vest in and belong to the Society."),
    Definition("PAAA", "means the Permanent Alternate Accommodation Agreement to be executed and registered between the Developer, the Society and each Existing Member in respect of the Members’ New Premises substantially in the format set out in [[ann:paaa]]."),
    Definition("Permanent Alternate Accommodation", "means the Members’ New Premises to be provided to each Existing Member in lieu of his / her / their Existing Premises."),
    Definition("PMC", "means the Project Management Consultant appointed by the Society from time to time, presently {{pmc.name}}."),
    Definition("Possession Date", "means, in relation to an Existing Member, the date on which possession of the Members’ New Premises is actually delivered to such Existing Member in accordance with [[art:possession]], or the date of expiry of the period stipulated in a Valid Possession Notice where the Existing Member fails to take possession without reasonable cause, whichever is earlier."),
    Definition("Possession Notice", "means the written notice to be issued by the Developer in terms of [[ref:poss_notice]]; and “Valid Possession Notice” means a Possession Notice issued only after the conditions in [[ref:poss_conditions]] have been fulfilled."),
    Definition("Project", "means the redevelopment of the Property by the Developer in accordance with this Agreement."),
    Definition("Rehabilitation Component", "means the Members’ New Premises, the Society office and the Common Areas and Amenities."),
    Definition("Rent", "means the monthly displacement compensation payable by the Developer to each Existing Member in terms of [[ref:rent]] to enable the Existing Member to procure temporary alternate accommodation."),
    Definition("RERA", "means the Real Estate (Regulation and Development) Act, 2016, the rules and regulations framed thereunder by the State of Maharashtra and the orders and circulars of the Maharashtra Real Estate Regulatory Authority."),
    Definition("RERA Carpet Area", "means carpet area as defined in Section 2(k) of RERA. Balcony, verandah and exclusive open terrace areas, where provided, shall be stated separately and shall not be included in the RERA Carpet Area unless expressly so stated."),
    Definition("UDCPR", "means the Unified Development Control and Promotion Regulations for Maharashtra State, as amended from time to time."),
    Definition("Vacation Notice", "means the written notice to be issued by the Developer in terms of [[ref:vac_notice]] after fulfilment of all conditions precedent set out in [[ref:vacation_cp]]."),
]

LIB_DEF = L("Definitions and interpretation", "Preferred",
            "Undefined or inconsistently used terms create ambiguity about the trigger for rent cessation, possession and completion.",
            "Indian Contract Act, 1872 (construction of contracts); General Clauses Act, 1897",
            "Defines completion and possession triggers by Full Occupation Certificate and actual readiness; separates units and members.")

INTERPRETATION = [
    c("int.1", "headings and the table of contents are for convenience only and shall not affect interpretation;"),
    c("int.2", "references to Articles, Clauses, Schedules and Annexures are to those of this Agreement;"),
    c("int.3", "the singular includes the plural and vice versa, and words importing a gender include every gender;"),
    c("int.4", "references to any law include that law as amended, re-enacted or substituted, and all subordinate legislation thereunder;"),
    c("int.5", "the words “include” and “including” are illustrative and shall not limit the generality of the preceding words;"),
    c("int.6", "areas are RERA Carpet Areas unless expressly stated otherwise, and 1 square metre shall be taken as 10.764 square feet;"),
    c("int.7", "where any period is to be computed from an event, the day of the event shall be excluded and, if the last day is not a working day, the period shall end on the next working day;"),
    c("int.8", "no provision of this Agreement shall be construed against the Society by reason of the Society or its advisors having drafted it;"),
    c("int.9", "in case of any inconsistency between this Agreement and any PAAA, Power of Attorney or other document executed pursuant hereto, this Agreement shall prevail, save where such other document is more beneficial to the Society or the Existing Members;"),
    c("int.10", "nothing in this Agreement shall be construed as a waiver by the Society or any Existing Member of any right or remedy available under Applicable Laws, including RERA, which cannot lawfully be waived."),
]

# --------------------------------------------------------------------------------------------
ARTICLES: list[Article] = [
    Article("I", "DEFINITIONS AND INTERPRETATION", [
        c("def.intro", "In this Agreement, unless the context otherwise requires, the capitalised terms set out in this Article shall have the meanings assigned to them below. Terms defined elsewhere in this Agreement shall have the meanings so assigned.", lib=LIB_DEF),
        c("def.list", "__DEFINITIONS__"),
        c("def.interp", "In this Agreement, unless the context otherwise requires:", *INTERPRETATION, h="Interpretation."),
        c("def.recitals", "The Recitals, Schedules and Annexures form an integral and operative part of this Agreement. The Parties confirm the correctness of the Recitals, save that the Society’s statements in the Recitals are made to the best of its knowledge on the basis of its records and the disclosures in [[sch:disclosures]]."),
    ]),
    Article("II", "PURPOSE AND APPOINTMENT OF DEVELOPER", [
        c("purpose", "The purpose of this Agreement is to record the terms on which the Society appoints the Developer to redevelop the Property, the consideration and entitlements receivable by the Society and the Existing Members, the security for the Developer’s performance and the mutual rights and obligations of the Parties."),
        c("appoint", "Pursuant to the procedure followed under the 79A Directions as recorded in the Recitals, the Society hereby appoints the Developer to carry out the redevelopment of the Property at the Developer’s own cost, risk and responsibility, and the Developer accepts such appointment, on the terms and conditions of this Agreement.",
          lib=L("Appointment of developer after Section 79A process", "Critical Society protection",
                "A DA executed without recording the 79A process is open to challenge by dissenting members.",
                "MCS Act, Section 79A and the 79A Directions", "Links appointment to the 79A process and the Accepted Offer.")),
        c("offer_binding", "The Developer confirms that the Accepted Offer has been incorporated into this Agreement. Any benefit, specification, amenity or commitment contained in the Accepted Offer or the tender submission of the Developer which is not expressly recorded herein shall nonetheless bind the Developer, and nothing in this Agreement shall be read as reducing any such benefit.",
          lib=L("Accepted Offer prevails where more beneficial", "Critical Society protection",
                "Developers often drop tender commitments while drafting the DA.", "Indian Contract Act, 1872, Sections 10, 62",
                "Prevents erosion of commitments made during the competitive tender.")),
        c("dev_standard", "The Developer shall perform its obligations diligently, in a good and workmanlike manner, in accordance with good industry practice, the sanctioned plans, Applicable Laws and this Agreement, and shall keep the Society and the PMC fully informed of the progress of the Project."),
        c("pmc_role", "The Society shall be entitled to act through the PMC and the Legal Advisor for supervision, inspection, verification and certification under this Agreement. The professional fees of the PMC and the Legal Advisor for the period from the date hereof until handover of the Society’s records under [[art:possession]] shall be borne by the Developer as part of the redevelopment cost, without the PMC or the Legal Advisor being thereby rendered accountable to the Developer.",
          lib=L("PMC supervision and fees", "Preferred", "Without independent supervision the Society relies on the Developer’s own certificates.", "", "PMC independence preserved even though Developer funds fees.")),
    ]),
    Article("III", "GRANT OF DEVELOPMENT RIGHTS", [
        c("grant", "In consideration of the Developer providing the Members’ New Premises and the other consideration set out in this Agreement, and subject to the Developer complying with this Agreement, the Society grants to the Developer the right to redevelop the Property by demolishing the Existing Buildings and constructing the New Building utilising the Development Potential, and to sell the Developer’s Free Sale Component in accordance with this Agreement (the “Development Rights”).",
          lib=L("Nature of development rights", "Critical Society protection",
                "Broad ‘transfer of FSI/land’ language can be read as a transfer of the Society’s leasehold interest.",
                "Transfer of Property Act, 1882, Section 53A; Registration Act, 1908, Section 17",
                "Development rights are contractual and conditional; no transfer of title.")),
        c("no_transfer", "Nothing in this Agreement shall be construed as a conveyance, transfer, lease or assignment of the Society’s leasehold rights in the Plot. The Society shall at all times remain the lessee of the Plot. The Developer shall not have any right, title or interest in the Plot other than the contractual Development Rights expressly granted herein."),
        c("licence", "The Developer shall, from the date hereof, have a revocable licence (which shall stand revoked upon termination of this Agreement) to enter upon the Property with prior intimation to the Society for surveys, soil investigation and measurements. Possession of the Property shall be delivered to the Developer only on the Handover Date, and such possession shall be as a licensee for the limited purpose of carrying out the Project and shall not be possession in part performance within the meaning of Section 53A of the Transfer of Property Act, 1882.",
          lib=L("Licence – not part performance", "Critical Society protection",
                "Irrevocable licence clauses disable the Society’s ability to recover the site upon termination.",
                "Transfer of Property Act, 1882, Section 53A; Indian Easements Act, 1882, Sections 52, 60", "")),
        c("cp_effect", "The obligation of the Society to deliver possession of the Property shall arise only upon fulfilment of each of the conditions precedent set out in [[ref:vacation_cp]]."),
        c("society_rights", "The Society shall retain the right (a) to inspect the site, records, test reports and accounts relating to the Rehabilitation Component through the PMC; (b) to approve, in a general body meeting, any change affecting the Rehabilitation Component, the Common Areas and Amenities or the external configuration of the New Building; and (c) to exercise all rights and remedies available under this Agreement and Applicable Laws."),
        c("limits", "The Developer shall not, without the prior written consent of the Society approved in a general body meeting: (a) amalgamate the Plot with any other land, or undertake cluster development; (b) load on the Plot any FSI or TDR in a manner which reduces the entitlements of the Existing Members; (c) create any encumbrance on the Plot or the Rehabilitation Component; or (d) do any act which may jeopardise the Society’s title to the Plot or its rights under the Lease Deed."),
    ]),
    Article("IV", "DEVELOPMENT POTENTIAL AND FSI", [
        c("fsi_use", "The Developer shall, at its own cost, procure and utilise the Development Potential available on the date of the Commencement Certificate, including basic FSI, premium FSI, ancillary / fungible FSI, incentive FSI and TDR, in accordance with the UDCPR and Applicable Laws, so as to construct the Rehabilitation Component and the Developer’s Free Sale Component."),
        c("fsi_statement", "The Developer has furnished, and the PMC has verified, an area statement of the Development Potential presently available, a summary whereof is: total Development Potential of {{tech.total_potential_sqm}} square metres; total RERA Carpet Area of the Members’ New Premises of {{tech.rehab_carpet_total_sqft}} square feet; and Developer’s Free Sale Component of {{tech.sale_carpet_total_sqft}} square feet. Any variation in the area statement shall not reduce the Members’ New Premises."),
        c("fsi_future", "If any Future FSI or additional development potential becomes available after the Commencement Certificate (including by reason of change in the UDCPR, road-widening, setback, reservation benefits or incentive schemes), the Developer shall not utilise the same without the prior approval of the Society in a general body meeting. The net benefit of such Future FSI, after deduction of the actual and documented premium, TDR cost, statutory charges and proportionate construction cost verified by the PMC, shall be shared between the Society (for the benefit of the Existing Members) and the Developer in the proportion agreed in such general body meeting, and in default of agreement, equally.",
          lib=L("Future FSI sharing", "Critical Society protection",
                "Developer-favourable drafts appropriate the entire benefit of later FSI increases.",
                "UDCPR (as amended); 79A Directions",
                "Requires SGBM approval and PMC-verified cost deduction before sharing.",
                neutral="Any Future FSI shall be utilised by the Developer and the net benefit thereof shall be shared between the Society and the Developer in the ratio set out in the Accepted Offer.")),
        c("fsi_costs", "All premiums, charges and costs claimed by the Developer for the purpose of computing the net benefit under [[ref:fsi_future]] shall be supported by receipts of the Authority and verified by the PMC. Notional, internal or unsupported costs shall not be deducted."),
        c("amalgamation", "Any proposal for amalgamation or cluster redevelopment shall be undertaken only with the prior approval of the Society in a general body meeting and a supplemental agreement, which shall not reduce the entitlements of the Existing Members or extend the Completion Date without the Society’s consent."),
        c("dcr_change", "If, owing to any change in Applicable Laws after the date hereof, the Development Potential is reduced, the Developer shall nevertheless provide the Members’ New Premises and all other consideration under this Agreement without reduction. Any increase shall be dealt with under [[ref:fsi_future]]."),
    ]),
    Article("V", "MEMBERS’ PERMANENT ENTITLEMENT", [
        c("ent_main", "The Developer shall construct and allot to each Existing Member, free of cost and without any consideration other than the surrender of the Existing Premises, the Members’ New Premises of the RERA Carpet Area set out against such Existing Member’s name in [[sch:members]], comprising the existing area together with the additional free area stated therein. Balcony and terrace areas, where applicable, are set out separately in [[sch:members]] and shall be provided in addition to the RERA Carpet Area.",
          lib=L("Members’ free entitlement", "Critical Society protection",
                "Entitlement stated only as a percentage or ‘as per plans’ can be reduced at sanction stage.", "RERA, Section 2(k) (carpet area)",
                "Unit-wise RERA carpet area fixed in a schedule.")),
        c("ent_parking", "Each Existing Member shall be allotted {{num:tech.parking_per_unit}} car parking space(s) per Existing Premises in the New Building free of cost, in accordance with [[sch:allocation]]. Allocation of parking spaces amongst the Existing Members shall be made by the Society by draw of lots or such other transparent method as the Society may decide, and shall be recorded in the PAAA."),
        c("ent_allocation", "The location (wing, floor and unit number) of the Members’ New Premises shall be allotted by the Society by draw of lots or other method decided in a general body meeting, out of the units earmarked as the Rehabilitation Component on the sanctioned plans, which shall be distributed across the floors of the New Building as set out in [[sch:allocation]] and shall not be confined to the lower floors save with the Society’s approval."),
        c("ent_amenities", "The Members’ New Premises shall be constructed in accordance with the specifications set out in [[sch:amenities]], which shall be not inferior to the specifications provided for the Developer’s Free Sale Component."),
        c("ent_measure", "Upon completion, the RERA Carpet Area of each of the Members’ New Premises shall be jointly measured by the Developer’s architect and the PMC. If the RERA Carpet Area is less than that set out in [[sch:members]] by more than {{tech.measurement_tolerance_percent}} per cent, the Developer shall pay to the concerned Existing Member compensation for the shortfall at the rate per square foot at which the Developer has sold comparable premises in the New Building, or the ready reckoner rate, whichever is higher, before the Possession Date.",
          lib=L("Measurement and deficiency compensation", "Critical Society protection",
                "No remedy where the delivered carpet area is short.", "RERA, Section 2(k); Section 14", "")),
        c("ent_additional", "An Existing Member may purchase additional area from the Developer at the rate set out in the Accepted Offer ({{tech.excess_area_rate}}), by a separate writing. Such purchase shall be a separate transaction; the stamp duty, registration charges and GST relating to such purchased area alone shall be borne by the concerned Existing Member, and the non-payment for such additional area shall not affect the free entitlement of the Existing Member under this Agreement.",
          when="tech.excess_area_rate"),
        c("ent_paaa", "The entitlement of each Existing Member shall be recorded in a PAAA to be executed and registered in accordance with [[ref:paaa_reg]]."),
        c("ent_office", "The Developer shall provide to the Society, free of cost, a furnished Society office in the New Building of the area required under Applicable Laws, together with the Common Areas and Amenities, all of which shall belong to the Society."),
    ]),
    Article("VI", "MONETARY CONSIDERATION", [
        c("rent", "From the Handover Date until the Possession Date of the concerned Existing Member, the Developer shall pay to each Existing Member Rent at the rate set out in [[sch:financials]] for each Existing Premises held by such Existing Member. Rent shall be paid monthly in advance on or before the {{comm.rent_due_day}} day of each calendar month by direct bank transfer to the account designated by the Existing Member and notified by the Society. The Developer shall, on the Handover Date, deposit post-dated cheques or a standing instruction acceptable to the Society for the first {{comm.rent_advance_months}} months.",
          h="Monthly Rent.",
          lib=L("Rent – payment, period and cessation", "Critical Society protection",
                "Rent stopping at ‘OC’ rather than at actual possession of ready premises.",
                "Indian Contract Act, 1872, Section 73",
                "Rent runs until the Possession Date, which requires a Valid Possession Notice issued after Full Occupation Certificate and readiness.",
                neutral="The Developer shall pay Rent from the Handover Date until the expiry of the period stipulated in the Possession Notice issued after receipt of the occupation certificate.")),
        c("rent_esc", "The Rent shall be escalated by {{comm.rent_escalation_percent}} per cent of the last paid Rent upon the expiry of every {{comm.rent_escalation_months}} months from the Handover Date. Escalation shall continue to apply during any extension of the Completion Date, whether on account of Force Majeure or otherwise.", h="Escalation."),
        c("rent_continuity", "The obligation to pay Rent is unconditional and shall not be suspended, reduced or withheld on account of Force Majeure, any dispute between the Parties, any pending arbitration or any default of an individual Existing Member (save as expressly provided in [[ref:noncons_deduct]]). Rent shall cease only on the Possession Date. Rent in respect of an Existing Member who is unable to take possession owing to a defect or deficiency in his / her / their Members’ New Premises shall continue until such defect or deficiency is rectified."),
        c("rent_delay", "If any instalment of Rent is not paid within {{comm.payment_grace_days}} days of its due date, the Developer shall pay interest at {{comm.delay_interest_percent}} per cent per annum on the delayed amount from the due date until payment, without prejudice to the Society’s rights under [[art:bg]] and [[art:termination]]."),
        c("brokerage", "On or before the Handover Date, the Developer shall pay to each Existing Member brokerage of {{money:comm.brokerage}} per Existing Premises for procuring temporary alternate accommodation, and a like amount upon the expiry of every period of eleven months thereafter until the Possession Date.", h="Brokerage."),
        c("deposit", "On or before the Handover Date, the Developer shall pay to each Existing Member an interest-free refundable deposit of {{money:comm.deposit}} per Existing Premises to enable the Existing Member to pay the security deposit for temporary alternate accommodation. The Existing Member shall refund the deposit within 30 (Thirty) days after the Possession Date, and the Developer may adjust the deposit only against such refund and against no other claim.", h="Refundable Security Deposit.", when="comm.deposit"),
        c("shifting", "The Developer shall pay to each Existing Member shifting charges of {{money:comm.shifting}} per Existing Premises on or before the Handover Date, and re-shifting charges of {{money:comm.reshifting}} per Existing Premises along with the Valid Possession Notice.", h="Shifting and Re-shifting Charges."),
        c("corpus", "The Developer shall pay to the Society a Corpus Fund of {{money:comm.corpus}} per Existing Premises, aggregating to the amount stated in [[sch:financials]]. The Corpus Fund shall be paid by the Developer to the Society directly and shall be held by the Society in a separate account; no part thereof shall be payable to any individual Existing Member except as the Society may decide. Unless otherwise provided in the Accepted Offer, 50 (Fifty) per cent of the Corpus Fund shall be paid on the Handover Date and the balance along with the Valid Possession Notice.", h="Corpus Fund.",
          lib=L("Corpus fund", "Preferred", "Corpus paid late or to individuals rather than the Society.", "Income-tax implications to be verified by tax advisor", "")),
        c("corpus_new", "The Developer shall additionally contribute {{money:comm.corpus_new_member}} towards the Society’s corpus in respect of each premises comprised in the Developer’s Free Sale Component, at the time of admission of the purchaser thereof to membership of the Society.", when="comm.corpus_new_member"),
        c("hardship", "The Developer shall pay to each Existing Member hardship compensation of {{money:comm.hardship}} per Existing Premises in the manner set out in [[sch:financials]].", h="Hardship Compensation.", when="comm.hardship"),
        c("office_rent", "The Developer shall provide temporary premises for the Society’s office during the Construction Period or pay the Society monthly rent of {{money:comm.society_office_rent}} for such premises, on the same terms as to escalation and payment as apply to Rent.", h="Temporary Society Office.", when="comm.society_office_rent"),
        c("addl_benefits", "In addition, the Developer shall provide the following benefits: {{comm.additional_benefits}}.", when="comm.additional_benefits"),
        c("taxes_payments", "All payments under this Article are net amounts receivable by the Society and the Existing Members. Any GST payable on the redevelopment service, and any tax required by law to be deducted at source, shall be dealt with in accordance with [[art:tax]]; where tax is deducted at source, the Developer shall issue the TDS certificate within the statutory period.", h="Taxes."),
        c("pay_mode", "All payments shall be made by direct bank transfer or account-payee instruments. Payments made to any person other than the Existing Member entitled thereto or the Society, as the case may be, shall not discharge the Developer. The Developer shall furnish to the Society, monthly, a statement of all payments made under this Article, which shall be reconciled by the PMC."),
        c("pay_schedule", "The member-wise statement of Rent, brokerage, deposit, shifting charges and other monetary consideration is set out in [[sch:financials]]."),
    ]),
    Article("VII", "BANK GUARANTEE AND PERFORMANCE SECURITY", [
        c("bg", "As security for the due performance of its obligations under this Agreement, the Developer shall furnish to the Society, before the issue of the Vacation Notice and in any event before the Handover Date, an unconditional, irrevocable and on-demand Bank Guarantee for {{money:security.bg_amount}} in the format set out in [[ann:bg_format]].",
          lib=L("Bank Guarantee – timing and nature", "Critical Society protection",
                "BG furnished after vacation, or conditional / encashable only after notice or award.",
                "Indian Contract Act, 1872, Section 126 (contract of guarantee); law on independence of unconditional bank guarantees to be verified by advocate",
                "BG is a condition precedent to vacation; on-demand; not subject to disputes.",
                neutral="The Developer shall furnish a Bank Guarantee of the agreed amount at the time of obtaining the Commencement Certificate.")),
        c("bg_bank", "The Bank Guarantee shall be issued by a scheduled commercial bank (not being a co-operative bank or small finance bank) having a branch at Navi Mumbai or Mumbai, and shall be payable at such branch."),
        c("bg_nature", "The Bank Guarantee shall be payable on first written demand of the Society, without demur, protest or reference to the Developer, and notwithstanding any dispute between the Parties or the pendency of any proceedings, including arbitration."),
        c("bg_validity", "The Bank Guarantee shall be valid until the expiry of the Defect Liability Period, or the Developer shall renew it not later than 30 (Thirty) days before its expiry, failing which the Society shall be entitled to invoke the entire amount and hold the proceeds as cash security on the same terms."),
        c("bg_invoke", "The Society may invoke the Bank Guarantee in whole or in part, after giving the Developer 15 (Fifteen) days’ written notice (save where the Bank Guarantee is about to expire, when no notice shall be required), upon (a) default in payment of Rent or any other amount under [[art:consideration]] for more than 30 (Thirty) days; (b) failure to complete the Project by the Completion Date; (c) any Developer Event of Default under [[ref:term_grounds]]; or (d) failure to renew or replenish the Bank Guarantee. Amounts so recovered shall be applied towards Rent and other dues of the Existing Members and towards the cost of completing the Project, and shall be without prejudice to the Society’s other rights."),
        c("bg_release", "The Bank Guarantee shall be reduced in stages in accordance with [[sch:bg]], upon completion of each milestone being certified in writing by the PMC (and not merely by the Developer’s architect), provided that there is no subsisting default of the Developer. The amount set out in [[sch:bg]] as retained during the Defect Liability Period shall be released only upon expiry of the Defect Liability Period and rectification of all notified defects."),
        c("bg_replenish", "If the Bank Guarantee is invoked in part, the Developer shall within 15 (Fifteen) days furnish a fresh Bank Guarantee for the amount invoked."),
        c("bg_additional", "The Developer shall also provide the following additional security: {{security.additional}}.", when="security.additional"),
        c("bg_fail", "Failure to furnish, renew or replenish the Bank Guarantee shall be a Developer Event of Default. Until the Bank Guarantee is furnished, the Society shall not be obliged to deliver possession of the Property, and the time for completion shall not be extended by reason thereof."),
    ]),
    Article("VIII", "REPRESENTATIONS AND WARRANTIES OF THE DEVELOPER", [
        c("dr_intro", "The Developer represents and warrants to the Society and the Existing Members, and acknowledges that the Society has relied upon such representations in appointing the Developer, that:",
          c("dr.const", "it is a {{developer.constitution}} duly constituted and validly existing under the laws of India and has full power and authority to execute and perform this Agreement;"),
          c("dr.auth", "the execution and performance of this Agreement have been duly authorised by all necessary corporate action and do not contravene its constitutional documents, any Applicable Law or any agreement binding on it;"),
          c("dr.fin", "it has the financial capacity, net worth and access to funding necessary to complete the Project without dependence on sale proceeds of the Developer’s Free Sale Component alone, and the financial statements and certificates furnished by it to the Society are true and correct;"),
          c("dr.solv", "no petition for insolvency, winding up, dissolution or appointment of a resolution professional, liquidator or receiver has been filed or is pending against it or its promoters, directors or partners, and it is not unable to pay its debts;"),
          c("dr.exp", "it has the experience, technical competence and resources to execute the Project, and the particulars of its completed and ongoing projects furnished to the Society are true;"),
          c("dr.lit", "save as disclosed in writing to the Society and set out in [[sch:disclosures]], there is no litigation, prosecution, regulatory proceeding or RERA complaint pending against it which may materially affect its ability to perform this Agreement;"),
          c("dr.disq", "neither it nor any of its directors, partners or promoters has been blacklisted, debarred or disqualified by any Authority, financial institution or court, nor convicted of any offence involving moral turpitude or economic offence;"),
          c("dr.rera", "it is not in default of any order of the Maharashtra Real Estate Regulatory Authority, and its RERA registrations are valid and in good standing;"),
          c("dr.enc", "it has not created and shall not create any encumbrance on the Property or the Development Rights, save as expressly permitted under [[ref:finance]];"),
          c("dr.statutory", "it shall comply with all Applicable Laws, including labour, environmental, safety and tax laws, in the performance of the Project."),
          lib=L("Developer representations", "Critical Society protection",
                "Bare representations without supporting documents or continuing obligation.", "Indian Contract Act, 1872, Sections 17-19 (fraud / misrepresentation)", "")),
        c("dr_docs", "The representations in this Article are made on the basis of, and shall be supported by, the documents listed in the execution checklist furnished to the Society, including audited financial statements, net-worth and solvency certificates and litigation disclosures. The Society shall not be deemed to have accepted any representation merely by reason of executing this Agreement."),
        c("dr_continuing", "The representations in this Article shall be deemed to be repeated on the Handover Date and on each date on which the Developer seeks release of any part of the Bank Guarantee. The Developer shall promptly notify the Society of any event which renders any representation untrue."),
    ]),
    Article("IX", "REPRESENTATIONS AND WARRANTIES OF THE SOCIETY AND THE EXISTING MEMBERS", [
        c("sr_intro", "The Society represents, to the best of its knowledge and on the basis of its records, that:",
          c("sr.lease", "the Society is the lessee of the Plot under the Lease Deed and is in lawful possession of the Property through the Existing Members;"),
          c("sr.members", "the particulars of the Existing Members and the Existing Premises set out in [[sch:members]] are as per the records of the Society;"),
          c("sr.resolutions", "the redevelopment of the Property and the appointment of the Developer have been approved in accordance with the MCS Act and the 79A Directions, as recorded in the Recitals;"),
          c("sr.encumbrance", "save as set out in [[sch:disclosures]], the Society has not created any mortgage, charge or third-party right over the Plot;"),
          c("sr.litigation", "save as set out in [[sch:disclosures]], the Society has not been served with any notice of acquisition or reservation, and is not aware of any litigation affecting the Property;"),
          c("sr.dues", "save as set out in [[sch:disclosures]], there are no lease rent, service charges or municipal dues outstanding in respect of the Plot as per the records of the Society."),
          lib=L("Society representations – knowledge-qualified", "Critical Society protection",
                "Absolute title warranties and indemnities expose the Society to liabilities for matters outside its knowledge.",
                "Indian Contract Act, 1872", "Representations are qualified by knowledge and by the disclosure schedule.")),
        c("sr_member", "Each Existing Member represents, in respect of his / her / their own Existing Premises only, that he / she / they is / are the member(s) of the Society entitled thereto and that, save as disclosed in [[sch:disclosures]] (including mortgages in favour of banks and pending transmission), the Existing Premises are free from encumbrances created by him / her / them. The liability of each Existing Member is several and limited to his / her / their own Existing Premises, and no Existing Member shall be liable for the act or default of any other Existing Member or of the Society."),
        c("sr_disclosure", "The Developer acknowledges that it has inspected the Property, the Lease Deed, the records of the Society and the disclosures in [[sch:disclosures]], and has satisfied itself as to the title of the Society and the Development Potential. No claim shall lie against the Society or the Existing Members in respect of any matter so disclosed or which the Developer ought reasonably to have discovered on such inspection."),
        c("sr_limit", "The Society shall not be liable to the Developer for any matter arising from the act or omission of the Developer, its contractors or agents, or from any change in Applicable Laws, and the indemnity of the Society under [[ref:indemnity_society]] shall be limited accordingly."),
    ]),
    Article("X", "DEVELOPER’S RIGHTS AND OBLIGATIONS", [
        c("do_intro", "Without prejudice to its other obligations under this Agreement, the Developer shall, at its own cost and risk:",
          c("do.approvals", "obtain all Approvals for the Project, including the Initial Approvals, the CIDCO no-objection certificate, environmental clearance (where applicable), fire, aviation, tree and other no-objection certificates, revised approvals and the Full Occupation Certificate, and comply with all conditions thereof;"),
          c("do.plans", "submit to the Society, before submission to the Authority, the proposed plans of the New Building, and obtain the Society’s written approval (granted in a general body meeting) to the layout, the location, size and configuration of the Members’ New Premises and the Common Areas and Amenities; any subsequent change affecting the Rehabilitation Component shall require the like approval, and the Developer shall comply with Section 14 of RERA in relation to the Developer’s Free Sale Component;"),
          c("do.demolition", "demolish the Existing Buildings after the Handover Date in accordance with Applicable Laws, remove the debris (which shall belong to the Developer), and take all precautions for the safety of adjoining properties and persons;"),
          c("do.construction", "construct the New Building in accordance with the sanctioned plans, the specifications in [[sch:amenities]], the National Building Code, applicable Indian Standards and good engineering practice, using new materials of the brands and grades specified;"),
          c("do.labour", "engage competent contractors and labour, comply with all labour laws (including the Building and Other Construction Workers laws, minimum wages and social security laws), pay labour cess, and be solely liable as principal employer for all claims of contractors, labour and suppliers;"),
          c("do.safety", "maintain site safety, barricading, insurance and watch-and-ward, comply with all safety regulations and be solely responsible for any accident, injury or death on or around the site during the Construction Period;"),
          c("do.mep", "provide all mechanical, electrical, plumbing, fire-fighting, lift, water supply, sewerage, sewage treatment, rain-water harvesting, solar and other services required under the Approvals and [[sch:amenities]], and obtain permanent electricity, water and drainage connections before the Valid Possession Notice;"),
          c("do.quality", "implement a quality assurance plan approved by the PMC, carry out third-party testing of concrete cubes, steel and other materials at a NABL-accredited laboratory, and furnish the test reports to the PMC monthly;"),
          c("do.inspection", "permit the PMC and the Society’s representatives to inspect the works at all reasonable times, and rectify at its cost any work found by the PMC to be defective or not in conformity with this Agreement;"),
          c("do.programme", "furnish to the Society within 30 (Thirty) days from the Commencement Certificate a detailed construction programme consistent with [[sch:timeline]], and thereafter monthly progress reports with photographs, the status of Approvals, payments made under [[art:consideration]] and the sales of the Developer’s Free Sale Component;"),
          c("do.statutory", "bear and pay all premiums, scrutiny fees, development charges, infrastructure charges, labour cess, deposits, GST and other statutory charges relating to the Approvals and the Project, and all municipal taxes, lease rent, service charges and outgoings of the Property from the Handover Date until the Possession Date;"),
          c("do.utilities", "shift and re-lay all utility services and connections required for the Project, and surrender and re-obtain the electricity meters, water connections and other services in the names of the Existing Members and the Society;"),
          c("do.records", "maintain and hand over to the Society, on completion, all approved plans, Approvals, structural drawings and calculations, as-built drawings, test reports, warranties, manuals and other project documents;"),
          c("do.rera", "register the Project under RERA, comply with all obligations of a promoter thereunder and furnish copies of all quarterly filings to the Society;"),
          c("do.noresale_rehab", "not sell, allot, mortgage or deal with any part of the Rehabilitation Component or the Common Areas and Amenities."),
          lib=L("Comprehensive developer obligations", "Critical Society protection",
                "Unrestricted ‘sole discretion’ powers over plans and amenities.", "RERA, Section 14; UDCPR; National Building Code", "")),
        c("finance", "The Developer may raise construction finance by creating a charge only on its rights in the Developer’s Free Sale Component and the receivables therefrom, after obtaining the Commencement Certificate and after furnishing the Bank Guarantee. The Developer shall not create any mortgage, charge or encumbrance over the Plot, the Society’s leasehold rights, the Rehabilitation Component, the Members’ New Premises or the Common Areas and Amenities. Every financing document shall expressly record that the lender shall have no recourse to the Rehabilitation Component and that the lender’s charge is subject to the rights of the Society and the Existing Members under this Agreement. The Developer shall furnish copies of all financing documents to the Society.",
          lib=L("No mortgage of rehabilitation entitlement", "Critical Society protection",
                "Lenders enforcing against members’ flats or the plot on developer default.",
                "Transfer of Property Act, 1882, Section 58; SARFAESI Act, 2002 (verify)",
                "Charge limited to free-sale component and receivables; lender acknowledges rehab priority.")),
        c("do_contractors", "The engagement of any contractor, consultant or agency shall not relieve the Developer of any of its obligations, and the Developer shall be liable for the acts and omissions of every such person as if they were its own."),
        c("do_insurance", "The Developer shall maintain the insurances described in [[ref:insurance]]."),
    ]),
    Article("XI", "OBLIGATIONS OF THE SOCIETY AND THE EXISTING MEMBERS", [
        c("so_cooperate", "Subject to the Developer performing its obligations, the Society shall: (a) sign such applications, plans and forms as may be reasonably required for obtaining the Approvals, which have first been reviewed by the PMC and the Legal Advisor; (b) furnish copies of documents in its possession relating to the Property; (c) cause the Existing Members to execute the PAAAs and vacate the Existing Premises in accordance with [[art:vacation]]; and (d) not create any third-party right over the Plot.",
          lib=L("Society obligations – reasonable cooperation", "Preferred",
                "Open-ended obligations to sign ‘all documents as the Developer may require’.", "", "")),
        c("so_authority", "All consents, approvals and communications on behalf of the Society under this Agreement shall be valid only if in writing, signed by at least two of the Chairman, the Secretary and the Treasurer, and, where this Agreement requires approval in a general body meeting, accompanied by a certified copy of the resolution of such meeting. The Developer shall not rely on any oral, informal or electronic-message communication, or on any communication from an individual office-bearer or Existing Member, as the consent of the Society.",
          lib=L("No informal consent through office-bearers", "Critical Society protection",
                "Clauses allowing the Developer to rely on any direction of a single office-bearer.",
                "MCS Act and bye-laws (powers of managing committee and general body)", "")),
        c("so_member_obligations", "Each Existing Member shall (a) execute and register the PAAA within the time stipulated in [[ref:paaa_reg]]; (b) clear the dues of the Society, electricity, water and municipal charges in respect of his / her / their Existing Premises up to the Handover Date; (c) obtain the no-objection of the bank or financial institution, if any, in whose favour the Existing Premises are mortgaged, the Developer providing such letters and undertakings as the lender may reasonably require; and (d) vacate the Existing Premises within the period stipulated in the Vacation Notice."),
        c("so_transfer", "An Existing Member may transfer his / her / their Existing Premises and the rights under this Agreement and the PAAA, with the prior approval of the Society in accordance with its bye-laws and Applicable Laws, provided that the transferee executes a deed of adherence agreeing to be bound by this Agreement. The Developer shall not have any right of first refusal or veto over such transfer, and shall recognise the transferee as an Existing Member upon intimation by the Society."),
        c("so_disputes", "Disputes inter se between Existing Members, or between the Society and any Existing Member, shall be dealt with by the Society in accordance with the MCS Act and its bye-laws. The Society shall use reasonable endeavours to resolve such disputes, but shall not be liable to the Developer for the consequences thereof except as provided in [[ref:noncons]]."),
    ]),
    Article("XII", "APPROVALS AND VACATION", [
        c("appr_period", "The Developer shall obtain the Initial Approvals within {{num:time.approval_months}} months from the date of this Agreement. If the Initial Approvals are not obtained within such period (as extended by the Society in writing, if at all), the Society may terminate this Agreement in accordance with [[art:termination]] without any liability to refund any amount spent by the Developer.",
          lib=L("Approval deadline separate from construction deadline", "Critical Society protection",
                "Open-ended approval stage leaves the Society bound indefinitely.", "", "")),
        c("vacation_cp", "The Developer shall not issue the Vacation Notice, and the Society and the Existing Members shall not be obliged to vacate the Existing Premises, unless and until each of the following conditions precedent has been fulfilled in the following sequence, and the PMC has certified in writing such fulfilment:",
          c("cp.1", "the Initial Approvals have been obtained;"),
          c("cp.2", "certified copies of the sanctioned plans and the Commencement Certificate have been furnished to the Society, and the sanctioned plans conform to this Agreement and the Members’ New Premises set out in [[sch:members]];"),
          c("cp.3", "the Bank Guarantee and the additional security, if any, have been furnished in accordance with [[art:bg]];"),
          c("cp.4", "the PAAAs have been executed and registered with all Existing Members who are ready and willing to do so;"),
          c("cp.5", "the brokerage, shifting charges, refundable deposit, the first instalment of the Corpus Fund, the advance Rent and other amounts payable on or before the Handover Date have been paid or deposited with the Society in accordance with [[art:consideration]];"),
          c("cp.6", "the Project has been registered under RERA; and"),
          c("cp.7", "the Developer has furnished the construction programme and evidence of construction finance or own funds sufficient to complete the Rehabilitation Component."),
          lib=L("Sequential conditions precedent to vacation", "Critical Society protection",
                "Members vacate before plans are sanctioned or security is furnished, leaving them without leverage.",
                "79A Directions (verify current requirements on timing of vacation)",
                "Vacation only after approvals, sanctioned plans, BG, registered PAAAs and initial payments.")),
        c("paaa_reg", "Within 15 (Fifteen) days of receipt of the Initial Approvals, the Developer shall furnish the final draft PAAA for each Existing Member, approved by the Legal Advisor, and the Existing Members shall execute and register the PAAAs within {{num:time.paaa_days}} days thereafter. The stamp duty and registration charges on the PAAAs shall be borne by the Developer in accordance with [[art:tax]]."),
        c("vac_notice", "Upon fulfilment of the conditions precedent in [[ref:vacation_cp]], the Developer may issue the Vacation Notice to the Society and to each Existing Member, enclosing the PMC’s certificate and copies of the documents evidencing such fulfilment. The Existing Members shall vacate the Existing Premises within {{num:time.vacation_notice_days}} days of receipt of the Vacation Notice."),
        c("handover", "Upon vacation of all the Existing Premises, the Society shall deliver possession of the Property to the Developer within 7 (Seven) days. A joint handover memorandum and inventory shall be signed by the Society, the PMC and the Developer recording the Handover Date, the condition of the Property and the meter readings, and the Developer shall issue a possession receipt to the Society in the format set out in [[ann:possession_receipt]]."),
        c("vac_undertaking", "Each Existing Member shall, at the time of vacating, deliver to the Society an undertaking in the format set out in [[ann:vacation_undertaking]]."),
        c("noncons", "If any Existing Member fails to vacate within the stipulated period despite fulfilment of the conditions precedent (a “Non-Cooperating Member”), the Society shall issue a notice to such Existing Member, and thereafter the Society and the Developer may jointly take proceedings, including under the MCS Act or the 79A Directions, to secure vacant possession. The costs of such proceedings shall be borne by the Developer in the first instance.",
          h="Non-Cooperating Members.",
          lib=L("Non-cooperating members – proportionate remedy", "Critical Society protection",
                "Developer-drafted clauses impose per-day penalties with high interest on members, which are likely unenforceable penalties and coercive.",
                "Indian Contract Act, 1872, Section 74; MCS Act; 79A Directions", "")),
        c("noncons_deduct", "The Developer may recover from the Non-Cooperating Member the reasonable and documented costs of such proceedings, and shall not be liable to pay Rent to such Non-Cooperating Member for the period of his / her / their delay in vacating. No other penalty or forfeiture shall be imposed on any Existing Member. The period of delay caused by Non-Cooperating Members shall extend the Completion Date only to the extent the PMC certifies that the delay actually prevented commencement of construction, and shall not affect the Rent, payments or entitlements of the other Existing Members."),
    ]),
    Article("XIII", "CONSTRUCTION AND COMPLETION", [
        c("completion_date", "The Developer shall complete the New Building in all respects, obtain the Full Occupation Certificate and issue a Valid Possession Notice within {{num:time.construction_months}} months from the Handover Date (the “Completion Date”). The Developer shall be entitled to a grace period of {{num:time.grace_months}} months beyond the Completion Date only upon continuing to pay the Rent and other amounts under [[art:consideration]], and liquidated damages under [[art:ld]] shall accrue from the expiry of the grace period.",
          lib=L("Completion defined by Full OC and readiness", "Critical Society protection",
                "Completion deemed on application for OC or on part OC; ‘parties shall fix new timeline’ clauses.",
                "RERA, Sections 11, 18", "",
                neutral="The Developer shall complete the Project and obtain the occupation certificate within the agreed period from the date of the Commencement Certificate.")),
        c("completion_meaning", "The Project shall be considered complete only when (a) the Full Occupation Certificate has been obtained; (b) permanent water, electricity and drainage connections are functional; (c) the lifts, fire-fighting systems, sewage treatment plant and other services are commissioned with valid certificates; (d) the Common Areas and Amenities are complete; and (e) the Members’ New Premises are complete in accordance with [[sch:amenities]] and ready for occupation. The application for or the deemed grant of an occupation certificate, or a part occupation certificate, shall not constitute completion."),
        c("monthly_reports", "The Developer shall submit monthly progress reports in accordance with [[ref:do.programme]]. If the PMC certifies that the progress of works is behind the construction programme by more than 3 (Three) months, the Developer shall within 15 (Fifteen) days submit a recovery plan acceptable to the PMC."),
        c("longstop", "If the Full Occupation Certificate is not obtained by the Long-Stop Date for reasons other than Force Majeure, the Society shall be entitled, without prejudice to its other rights, to terminate this Agreement under [[art:termination]], invoke the Bank Guarantee and appoint another developer to complete the Project."),
        c("rehab_priority", "The Developer shall not apply for any occupation certificate in respect of the Developer’s Free Sale Component alone, or deliver possession of any premises in the Developer’s Free Sale Component, before obtaining the Full Occupation Certificate and delivering possession of the Members’ New Premises in accordance with [[art:possession]]."),
    ]),
    Article("XIV", "FORCE MAJEURE", [
        c("fm_def", "“Force Majeure” means any of the following events, to the extent that it is beyond the reasonable control of the Developer, could not have been prevented by the exercise of reasonable diligence, and directly prevents or delays the performance of the Developer’s obligations: (a) war, invasion, act of foreign enemy, terrorism, riot or civil commotion in Navi Mumbai; (b) earthquake, flood, cyclone or other natural calamity of exceptional severity; (c) epidemic or pandemic accompanied by a lockdown or prohibition of construction activity ordered by an Authority; and (d) any order of a court or Authority restraining construction on the Plot which is not attributable to any act, omission or default of the Developer, its contractors or agents.",
          lib=L("Narrow, objective force majeure", "Critical Society protection",
                "Broad FM (material shortages, rule changes, any event ‘directly or indirectly’ affecting developer) excuses ordinary commercial risk.",
                "Indian Contract Act, 1872, Sections 32 and 56 (frustration)", "",
                neutral="Force Majeure shall include acts of God, war, pandemic, and orders of Authorities restraining construction not caused by the Developer.")),
        c("fm_excl", "The following shall not constitute Force Majeure: shortage of funds or financial difficulty of the Developer; market conditions or slow sales; increase in the price or shortage of materials or labour (save as a direct consequence of an event in [[ref:fm_def]]); default of contractors, suppliers or consultants; delay in obtaining Approvals due to the Developer’s failure to apply in time or to comply with requirements of the Authority; changes in Applicable Laws (which are governed by [[ref:dcr_change]]); and any delay attributable to the Developer."),
        c("fm_notice", "The Developer shall notify the Society in writing within 15 (Fifteen) days of the commencement of the Force Majeure event, with supporting documents, the obligations affected and the estimated period of delay, and shall take all reasonable steps to mitigate its effect. An extension of time shall be granted only for the period of actual delay demonstrated by the Developer and certified by the PMC."),
        c("fm_payments", "Force Majeure shall not suspend or excuse the payment of Rent, escalation or any other amount payable under this Agreement, which shall continue to be paid in full during the Force Majeure period."),
        c("fm_prolonged", "If a Force Majeure event continues for more than 180 (One Hundred and Eighty) days, the Parties shall meet to agree upon a revised programme; if a Force Majeure event continues for more than 365 (Three Hundred and Sixty-Five) days, the Society may terminate this Agreement by notice, and the consequences under [[ref:term_consequences]] shall apply, save that no damages shall be claimed by either Party for the Force Majeure period."),
    ]),
    Article("XV", "QUALITY AND DEFECT LIABILITY", [
        c("dlp", "The Developer shall, during the Defect Liability Period, rectify at its own cost any structural defect, defect in workmanship, quality or provision of services, including seepage, leakage, waterproofing failure, cracks (other than hairline cracks within tolerances certified by the PMC), and defects in the MEP systems, lifts, fire systems and Common Areas and Amenities, notified by the Society or any Existing Member.",
          lib=L("Defect liability – statutory floor", "Critical Society protection",
                "Exclusions that defeat Section 14(3) RERA rights or void DLP upon any alteration.",
                "RERA, Section 14(3)", "")),
        c("dlp_time", "The Developer shall commence rectification within 7 (Seven) days and complete it within 30 (Thirty) days of notice (or such longer period as the PMC may certify as reasonable for the nature of the defect). Emergency defects affecting safety or habitability shall be attended to within 48 (Forty-Eight) hours."),
        c("dlp_inspection", "In case of disagreement as to whether a defect exists or its cause, the matter shall be referred to an independent structural or MEP consultant appointed by the PMC, whose report shall be binding for the purpose of this Article; the cost shall be borne by the Developer if the defect is established."),
        c("dlp_selfhelp", "If the Developer fails to rectify a defect within the period stipulated in [[ref:dlp_time]], the Society may get the defect rectified through another agency and recover the cost with interest at {{comm.delay_interest_percent}} per cent per annum from the Developer or from the Bank Guarantee retained under [[ref:bg_release]]."),
        c("dlp_member_works", "The Developer shall not be liable for a defect to the extent it is shown to have been caused by alterations made by an Existing Member to the structure or services, but such alterations shall not otherwise affect the Defect Liability Period or the Developer’s liability for other defects."),
        c("dlp_warranties", "The Developer shall obtain and assign to the Society all manufacturers’ warranties for lifts, pumps, generators, sewage treatment plant, fire systems and other equipment, and shall provide comprehensive annual maintenance contracts for the lifts and fire systems for the first 2 (Two) years after the Possession Date at its own cost."),
    ]),
    Article("XVI", "POSSESSION AND HANDOVER", [
        c("poss_conditions", "The Developer shall be entitled to issue a Possession Notice only after: (a) obtaining the Full Occupation Certificate; (b) the Members’ New Premises being complete in accordance with this Agreement and ready for occupation, with functional water, electricity, drainage and lift services; (c) completion of the Common Areas and Amenities; (d) joint measurement under [[ref:ent_measure]]; (e) payment of all Rent and other amounts due up to that date; and (f) the PMC certifying the fulfilment of the above.",
          lib=L("No deemed possession", "Critical Society protection",
                "Deemed possession on mere notice even if premises are not legally and practically ready.",
                "RERA, Sections 11(4)(b), 17, 19(10)", "")),
        c("poss_notice", "The Developer shall issue the Possession Notice to the Society and each Existing Member, enclosing the Full Occupation Certificate and the PMC’s certificate. Each Existing Member shall take possession within {{num:time.possession_take_days}} days of receipt of a Valid Possession Notice, after a joint inspection; any defects noted at such inspection shall be rectified within 30 (Thirty) days without prejudice to the Defect Liability Period."),
        c("poss_docs", "On or before the Possession Date the Developer shall deliver to the Society: certified copies of all Approvals and the Full Occupation Certificate; the approved and as-built plans; structural stability and design certificates; fire-safety completion certificate; lift licences and certificates; warranties, manuals and the annual maintenance contracts under [[ref:dlp_warranties]]; the parking allocation; keys of the common areas; and all documents required for the Society to maintain the New Building."),
        c("poss_letter", "Possession of the Members’ New Premises shall be delivered against a possession letter which shall record any pending defects and shall not contain any waiver of the rights of the Existing Member or the Society."),
        c("lease_amend", "The Developer shall, at its own cost, obtain such permissions from CIDCO and execute such documents as may be required to record the New Building and the membership of the purchasers of the Developer’s Free Sale Component, within {{num:time.lease_amendment_months}} months from the Full Occupation Certificate, without affecting the Society’s leasehold rights."),
    ]),
    Article("XVII", "DEVELOPER’S FREE SALE COMPONENT", [
        c("free_sale", "Subject to the Developer complying with this Agreement, the Developer shall be entitled to sell the Developer’s Free Sale Component and to receive the sale proceeds thereof. The Developer shall not commence sale of any premises before the Handover Date and the registration of the Project under RERA.",
          lib=L("Separation of developer’s commercial rights", "Critical Society protection",
                "Society made liable for purchaser claims.", "RERA, Sections 2(zk), 11, 13, 18", "")),
        c("fs_principal", "All agreements with purchasers shall be entered into by the Developer in its own name, as principal and not as agent of the Society. The Developer alone shall be liable to the purchasers for all obligations, refunds, interest and compensation, and the Society and the Existing Members shall not be liable in any manner."),
        c("fs_afs", "Every agreement for sale shall disclose this Agreement, shall record that the purchaser’s rights are subject to the rights of the Society and the Existing Members hereunder, and shall bind the purchaser to become a member of the Society and abide by its bye-laws."),
        c("fs_membership", "The Society shall admit the purchasers of the Developer’s Free Sale Component as members in accordance with its bye-laws after the Possession Date of all the Existing Members, upon payment of the share money, entrance fee and the corpus contribution, if any, payable under [[art:consideration]] and production of a no-dues certificate from the Developer."),
        c("fs_unsold", "The Developer shall pay the maintenance charges and outgoings of unsold premises in the Developer’s Free Sale Component from the Possession Date."),
        c("fs_signage", "The Developer may display its name and brand on the New Building during the Construction Period and for 6 (Six) months after the Full Occupation Certificate. Any permanent signage shall require the approval of the Society."),
    ]),
    Article("XVIII", "RERA", [
        c("rera_reg", "The Developer shall register the Project under RERA as promoter before any advertisement or sale, and shall comply with all obligations of a promoter under RERA. The Developer shall deposit the prescribed percentage of the amounts realised from the purchasers in the separate account maintained under Section 4(2)(l)(D) of RERA and use such amounts only for the purposes permitted thereby.",
          lib=L("RERA allocation", "Critical Society protection",
                "Society unknowingly assuming promoter liabilities, or ‘joint’ registration without allocation.",
                "RERA, Sections 2(zk), 3, 4(2)(l)(D), 11, 14, 18; MahaRERA orders on landowner / society as promoter (verify)",
                "Developer is the promoter; where Society must be shown as co-promoter, its liability is confined to title and the Developer indemnifies.")),
        c("rera_society", "Where Applicable Laws or MahaRERA require the Society to be disclosed or registered as a co-promoter or landowner-promoter, the Society’s obligations shall be limited, as between the Parties, to matters of title to the Plot. All other obligations and liabilities of a promoter shall be borne exclusively by the Developer, who shall indemnify the Society and the Existing Members in accordance with [[art:indemnity]]. Nothing herein shall be construed as the Society contracting out of any statutory liability vis-à-vis third parties; this allocation operates as between the Parties."),
        c("rera_members", "The Parties acknowledge that the Existing Members may be entitled to the rights of allottees under RERA in respect of the Members’ New Premises, and nothing in this Agreement shall prejudice such rights."),
        c("rera_docs", "The Developer shall furnish to the Society copies of all filings, quarterly progress reports and certificates submitted to MahaRERA."),
    ]),
    Article("XIX", "TAXATION, GST AND STAMP DUTY", [
        c("tax_gst", "Any GST, by whatever name called, payable in respect of the construction and delivery of the Members’ New Premises, the Rehabilitation Component and the transfer of Development Rights shall be borne and paid by the Developer, and shall not be recovered from the Society or the Existing Members.",
          lib=L("GST and stamp duty economic burden", "Preferred",
                "Members asked to pay GST on free rehabilitation premises.", "CGST Act, 2017 and notifications on development rights / redevelopment (verify current position); Maharashtra Stamp Act, 1958",
                "")),
        c("tax_stamp", "The stamp duty, registration charges and incidental expenses on this Agreement, the Power of Attorney, the PAAAs, the deeds of confirmation and all documents executed in pursuance hereof shall be borne by the Developer. Stamp duty and registration charges on any additional area purchased by an Existing Member shall be borne by such Existing Member."),
        c("tax_direct", "Each Party shall bear its own income-tax liability. The Developer shall bear any tax required to be deducted at source by it on payments to the Existing Members and shall issue certificates thereof. The Developer shall indemnify the Society and the Existing Members against any tax, interest or penalty arising from its non-compliance."),
        c("tax_property", "Property tax, lease rent and service charges on the Property shall be borne by the Developer from the Handover Date until the Possession Date, and thereafter in respect of the unsold premises of the Developer’s Free Sale Component."),
    ]),
    Article("XX", "DELAY AND LIQUIDATED DAMAGES", [
        c("ld", "If the Developer fails to issue a Valid Possession Notice by the expiry of the grace period under [[ref:completion_date]], the Developer shall pay to the Society, for the benefit of the Existing Members, liquidated damages of {{money:security.ld_per_month}} per month or part thereof of delay, in addition to and not in substitution of the Rent and escalation, which shall continue to be payable.",
          lib=L("Liquidated damages in addition to rent", "Critical Society protection",
                "LD credited against rent, or LD payable only if delay is ‘solely’ attributable to the developer.",
                "Indian Contract Act, 1872, Section 74", "The LD figure must be a genuine pre-estimate; record the basis in the Accepted Offer.")),
        c("ld_basis", "The Parties agree that the liquidated damages represent a genuine pre-estimate of the loss likely to be suffered by the Society and the Existing Members on account of prolonged displacement, loss of use and increased costs, having regard to the number of Existing Premises and the prevailing rental market, and are not a penalty."),
        c("ld_recovery", "Liquidated damages shall be paid monthly and may be recovered from the Bank Guarantee. Payment of liquidated damages shall not relieve the Developer of its obligation to complete the Project, nor prejudice the Society’s right to terminate under [[art:termination]] after the Long-Stop Date."),
        c("ld_exclusion", "Liquidated damages shall not accrue for any period of delay certified by the PMC as having been caused by Force Majeure or by a breach of this Agreement by the Society."),
    ]),
    Article("XXI", "TERMINATION", [
        c("term_grounds", "Each of the following shall be a “Developer Event of Default”:",
          c("tg.1", "failure to obtain the Initial Approvals within the period stipulated in [[ref:appr_period]];"),
          c("tg.2", "failure to commence construction within 3 (Three) months from the Handover Date, or suspension of work for a continuous period of 3 (Three) months, other than due to Force Majeure;"),
          c("tg.3", "failure to pay Rent or any other amount under [[art:consideration]] for 2 (Two) consecutive months, or on 3 (Three) occasions in any 12 (Twelve) month period;"),
          c("tg.4", "failure to furnish, renew or replenish the Bank Guarantee;"),
          c("tg.5", "failure to obtain the Full Occupation Certificate by the Long-Stop Date;"),
          c("tg.6", "creation of any encumbrance in breach of [[ref:finance]], or assignment or change of control in breach of [[ref:assign_bar]];"),
          c("tg.7", "insolvency, winding up, admission of an insolvency petition, appointment of a receiver or resolution professional, or the Developer being unable to pay its debts;"),
          c("tg.8", "material deviation from the sanctioned plans or specifications affecting the Rehabilitation Component, or any representation in [[art:dev_reps]] being found to be materially untrue; and"),
          c("tg.9", "any other material breach of this Agreement."),
          lib=L("Comprehensive termination grounds", "Critical Society protection",
                "Termination limited to a single ground, or exercisable only through an arbitral award.",
                "Indian Contract Act, 1872, Sections 39, 55, 73; Arbitration and Conciliation Act, 1996, Section 9",
                "Society may terminate after cure period without awaiting an award; disputes go to arbitration thereafter.",
                neutral="Either party may terminate for material breach not cured within 60 days of notice, subject to arbitration.")),
        c("term_cure", "Upon a Developer Event of Default, the Society may issue a notice to the Developer specifying the default. If the default (being capable of remedy) is not remedied within {{num:time.cure_days}} days of such notice (or 30 (Thirty) days in the case of default in payment), the Society may, after obtaining the written opinion of the PMC and the Legal Advisor and the approval of a general body meeting, terminate this Agreement by written notice. Defaults under [[ref:tg.5]] and [[ref:tg.7]] shall not require any cure period."),
        c("term_consequences", "Upon termination for a Developer Event of Default:",
          c("tc.1", "the Development Rights, the licence and the Power of Attorney shall stand revoked, and the Developer shall forthwith hand over the site, the works executed, all Approvals, plans, documents and records to the Society;"),
          c("tc.2", "the Society may invoke the Bank Guarantee and the additional security, and appoint another developer to complete the Project;"),
          c("tc.3", "the Developer shall not be entitled to any refund or reimbursement of amounts paid to the Existing Members or the Society, or of costs incurred by it, save to the extent that the Society, upon appointment of a new developer, actually receives from such new developer an amount specifically towards the value of the work executed by the Developer as certified by the PMC, after deduction of all losses, damages and costs suffered by the Society and the Existing Members;"),
          c("tc.4", "the Developer shall co-operate in the transfer of Approvals and RERA registration to the new developer, and shall remain liable to the purchasers of the Developer’s Free Sale Component;"),
          c("tc.5", "the Society shall be entitled to recover from the Developer all losses, damages and costs in accordance with law."),
          lib=L("No automatic reimbursement on termination", "Critical Society protection",
                "Clauses requiring the Society to refund all developer expenditure before appointing a new developer.",
                "Indian Contract Act, 1872, Sections 65, 73, 74", "")),
        c("term_arb", "The right of the Society to terminate under this Article shall not be conditional upon any prior arbitral award. Any dispute regarding the validity of termination may be referred to arbitration under [[ref:arbitration]], but the pendency of such proceedings shall not prevent the Society from invoking the Bank Guarantee or appointing another developer, save as may be ordered by a court or arbitral tribunal of competent jurisdiction."),
        c("term_society", "The Developer may terminate this Agreement only if the Society fails to deliver possession of the Property within 6 (Six) months after fulfilment of all conditions precedent in [[ref:vacation_cp]] for reasons solely attributable to the Society, after giving 60 (Sixty) days’ notice to remedy. In such event the Developer’s sole remedy shall be the return of the Bank Guarantee and refund of amounts actually paid to the Society (not to individual Existing Members) under this Agreement."),
        c("term_survival", "Termination shall be without prejudice to the accrued rights of the Parties and to the provisions which are expressed or intended to survive termination."),
    ]),
    Article("XXII", "INDEMNITY AND INSURANCE", [
        c("indemnity_dev", "The Developer shall indemnify and keep indemnified the Society, its office-bearers and the Existing Members against all losses, claims, demands, penalties, costs (including legal costs) and liabilities arising from or in connection with:",
          c("id.1", "any breach of Applicable Laws or Approvals by the Developer, its contractors or agents;"),
          c("id.2", "construction defects and any accident, injury or death on or around the site;"),
          c("id.3", "claims of labour, contractors, suppliers and consultants engaged by or through the Developer;"),
          c("id.4", "claims of purchasers of the Developer’s Free Sale Component and any liability under RERA attributable to the Developer;"),
          c("id.5", "tax defaults of the Developer;"),
          c("id.6", "environmental violations;"),
          c("id.7", "any encumbrance created by the Developer; and"),
          c("id.8", "any breach of this Agreement by the Developer."),
          lib=L("Developer indemnity without caps or narrow exclusions", "Critical Society protection",
                "Indemnity limited to ‘solely negligent’ acts, capped, time-limited to handover, or subject to the developer’s sole conduct of defence.",
                "Indian Contract Act, 1872, Sections 124-125", "")),
        c("indemnity_society", "The Society shall indemnify the Developer only against direct losses actually suffered by reason of any representation of the Society in [[art:society_reps]] being false to the knowledge of the Society, and the Existing Members shall each be liable only in respect of their own Existing Premises. Loss of profit, holding cost and other indirect or consequential losses shall be excluded."),
        c("insurance", "The Developer shall, from the Handover Date until the Possession Date, maintain with a reputed insurer a contractor’s all-risk policy for the full value of the works, third-party liability insurance, workmen’s compensation insurance and such other insurance as may be required under Applicable Laws, naming the Society as co-insured or loss-payee in respect of the Rehabilitation Component, and shall furnish copies of the policies to the Society.", h="Insurance."),
        c("ind_survival", "The indemnities in this Article shall survive the completion and termination of this Agreement."),
    ]),
    Article("XXIII", "MISCELLANEOUS", [
        c("assign_bar", "The Developer shall not assign, transfer or sub-contract the whole or substantially the whole of the Development Rights or this Agreement, or enter into any joint venture or development management arrangement in respect thereof, without the prior written approval of the Society in a general body meeting. Any change in the shareholding, partnership or control of the Developer resulting in the present promoters ceasing to hold at least 51 (Fifty-One) per cent of the voting rights or ceasing to control the Developer shall be deemed to be an assignment requiring such approval.", h="No assignment; change of control."),
        c("poa", "Simultaneously with this Agreement, the Society shall execute a Power of Attorney in favour of the Developer substantially in the format set out in [[ann:poa]], limited to the acts required for obtaining Approvals and for the sale of the Developer’s Free Sale Component. The Power of Attorney shall be co-extensive with this Agreement, shall not authorise any act in relation to the Rehabilitation Component or any encumbrance of the Plot, and shall stand revoked upon termination of this Agreement.", h="Power of Attorney.",
          lib=L("Limited, co-terminus power of attorney", "Critical Society protection",
                "Irrevocable general POA that survives termination and permits dealings with the plot.", "Indian Contract Act, 1872, Sections 201-202; Registration Act, 1908", "")),
        c("notices", "All notices under this Agreement shall be in writing and delivered by hand against acknowledgement, by registered post A.D. or speed post, or by email with a copy by one of the foregoing methods, to the addresses set out below or such other address as may be notified: to the Society at {{society.address}} (email: {{society.email}}), with a copy to the PMC and the Legal Advisor; and to the Developer at {{developer.address}} (email: {{developer.email}}).", h="Notices."),
        c("nonwaiver", "No failure or delay by the Society or any Existing Member in exercising any right shall operate as a waiver thereof. No waiver shall be effective unless in writing and approved in accordance with [[ref:so_authority]]; and no conduct, acceptance of payment, participation in meetings, oral or electronic communication shall constitute waiver of any breach.", h="Non-waiver."),
        c("confidential", "Each Party shall keep confidential the terms of this Agreement and the information of the Existing Members, save as required by Applicable Laws, for the purposes of the Project, or for disclosure to professional advisors and financiers bound by confidentiality. The Developer shall process personal information of the Existing Members only for the purposes of this Agreement and in accordance with Applicable Laws relating to data protection.", h="Confidentiality."),
        c("entire", "This Agreement, together with the Accepted Offer, constitutes the entire agreement between the Parties and supersedes all prior understandings, save that the Accepted Offer shall prevail to the extent provided in [[ref:offer_binding]].", h="Entire agreement."),
        c("amend", "No amendment of this Agreement shall be effective unless made in writing, approved by the Society in a general body meeting and signed by the authorised office-bearers of the Society and the Developer. Minutes of meetings, correspondence and electronic messages shall not amend this Agreement.", h="Amendments."),
        c("severability", "If any provision of this Agreement is held invalid or unenforceable, the remaining provisions shall continue in full force and the Parties shall substitute a valid provision which most closely achieves the intent of the invalid provision.", h="Severability."),
        c("further", "Each Party shall execute such further documents as may be reasonably necessary to give effect to this Agreement, provided that no such document shall impose any obligation on the Society or the Existing Members beyond those contained herein.", h="Further assurances."),
        c("relationship", "Nothing in this Agreement shall constitute a partnership, joint venture or agency between the Society and the Developer.", h="Relationship."),
        c("governing", "This Agreement shall be governed by the laws of India.", h="Governing law."),
        c("arbitration", "Any dispute arising out of or in connection with this Agreement shall, after an attempt at amicable resolution for 30 (Thirty) days, be referred to arbitration by a sole arbitrator appointed by mutual consent (and failing such consent, in accordance with the Arbitration and Conciliation Act, 1996), who shall be independent of both Parties. The seat of arbitration shall be {{exec.arbitration_seat}} and the language shall be English. The costs of arbitration shall be borne as awarded by the arbitrator. Nothing herein shall prevent the Society from (a) seeking interim relief from a competent court under Section 9 of the Arbitration and Conciliation Act, 1996; (b) invoking the Bank Guarantee; or (c) terminating this Agreement in accordance with [[art:termination]]. Disputes between the Society and its members which fall within Section 91 of the MCS Act shall be governed by that Act.", h="Arbitration.",
          lib=L("Arbitration not a bar to Society remedies", "Critical Society protection",
                "Arbitration-before-termination clauses and cost sharing that disable the Society.",
                "Arbitration and Conciliation Act, 1996, Sections 9, 11, 12, 29A; MCS Act, Section 91", "")),
        c("jurisdiction", "Subject to [[ref:arbitration]], the courts at {{exec.courts}} shall have exclusive jurisdiction.", h="Jurisdiction."),
        c("survival", "The provisions of [[art:indemnity]], [[art:tax]], [[ref:ld_recovery]], [[ref:term_consequences]], [[ref:confidential]], [[ref:arbitration]] and the Defect Liability Period obligations shall survive termination or completion of this Agreement.", h="Survival."),
        c("counterparts", "This Agreement shall be executed in a single original to be retained by the Society, and the Developer shall be furnished a certified copy after registration.", h="Original."),
    ]),
]

# Map of article anchor ids used in [[art:...]] references.
ARTICLE_ANCHORS = {
    "definitions": "I", "appointment": "II", "grant": "III", "fsi": "IV", "entitlement": "V",
    "consideration": "VI", "bg": "VII", "dev_reps": "VIII", "society_reps": "IX", "dev_obligations": "X",
    "society_obligations": "XI", "vacation": "XII", "completion": "XIII", "force_majeure": "XIV",
    "dlp": "XV", "possession": "XVI", "free_sale": "XVII", "rera": "XVIII", "tax": "XIX", "ld": "XX",
    "termination": "XXI", "indemnity": "XXII", "misc": "XXIII",
}
