"""Formats of the generated annexures (Bank Guarantee, PAAA, Vacation Undertaking, POA, Possession Receipt).

Same placeholder syntax as master_da.py. Paragraph lists; a leading "## " marks a sub-heading.
"""

SCHEDULES = [  # (key, title, subtitle)
    ("property", "FIRST SCHEDULE", "Description of the Plot"),
    ("existing", "SECOND SCHEDULE", "Description of the Existing Buildings and Existing Premises"),
    ("members", "THIRD SCHEDULE", "Member-wise Existing Premises and Members’ New Premises (Area Entitlement)"),
    ("allocation", "FOURTH SCHEDULE", "Rehabilitation Allocation and Parking Allocation"),
    ("financials", "FIFTH SCHEDULE", "Member-wise Rent and Monetary Consideration"),
    ("amenities", "SIXTH SCHEDULE", "Common Areas and Amenities and Specifications"),
    ("bg", "SEVENTH SCHEDULE", "Bank Guarantee and Performance Security – Submission and Release"),
    ("timeline", "EIGHTH SCHEDULE", "Project Completion Schedule"),
    ("disclosures", "NINTH SCHEDULE", "Disclosure Schedule – Litigation, Encumbrances, Mortgages and Pending Transmissions"),
]

# key, title, kind ("copy" = copy of an existing document to be annexed; "format" = generated text)
ANNEXURES = [
    ("sgbm_resolution", "Certified copy of the resolution of the Special General Body Meeting approving this Agreement", "copy", ["sgbm_minutes"]),
    ("board_resolution", "Certified copy of the resolution of the Developer authorising execution", "copy", ["developer_board_resolution"]),
    ("reg_cert", "Copy of the Certificate of Registration of the Society", "copy", ["society_registration"]),
    ("order79a", "Copy of the order of the Deputy Registrar under the 79A Directions", "copy", ["order_79a"]),
    ("offer", "Copy of the Accepted Offer of the Developer", "copy", ["final_offer"]),
    ("bg_format", "Format of Bank Guarantee", "format", []),
    ("paaa", "Format of Permanent Alternate Accommodation Agreement", "format", []),
    ("vacation_undertaking", "Format of Vacation Undertaking", "format", []),
    ("poa", "Format of Power of Attorney", "format", []),
    ("possession_receipt", "Format of Handover Memorandum, Possession Receipt and Inventory", "format", []),
    ("plans", "Copy of the proposed plans and architect’s area statement verified by the PMC", "copy", ["area_statement", "plans"]),
]

BG_FORMAT = [
    "## (To be issued on non-judicial stamp paper of appropriate value by a scheduled commercial bank)",
    "To,\n{{society.name}},\n{{society.address}}.",
    "WHEREAS by a Development Agreement dated ______________ (the “Agreement”) executed between {{society.name}} (the “Society”) and {{developer.name}} (the “Developer”), the Developer is required to furnish to the Society an unconditional and irrevocable guarantee of a bank for {{money:security.bg_amount}} as security for the due performance of its obligations under the Agreement.",
    "NOW THEREFORE, we, ______________ Bank, having our branch at ______________ (the “Bank”), at the request of the Developer, hereby irrevocably and unconditionally undertake to pay to the Society, on its first written demand and without any demur, protest, reservation or reference to the Developer, any sum or sums up to a maximum of {{money:security.bg_amount}}.",
    "Any demand made by the Society shall be conclusive and binding on the Bank as regards the amount due and payable, notwithstanding any dispute raised by the Developer or pending before any court, tribunal or arbitrator. The Bank shall not be entitled to call upon the Society to prove any default or loss.",
    "This guarantee shall not be affected by any change in the constitution of the Bank or the Developer, any variation of the Agreement, any extension of time or indulgence granted to the Developer, or the insolvency of the Developer.",
    "This guarantee shall remain in force until ______________ (being not earlier than the expiry of the Defect Liability Period) and shall be extended by the Bank at the request of the Developer. A demand made before the expiry date shall be honoured notwithstanding that payment falls due after expiry.",
    "The Bank undertakes not to revoke this guarantee during its currency except with the prior written consent of the Society. Claims hereunder shall be payable at our branch at Navi Mumbai / Mumbai.",
    "Dated this ____ day of ______________, 20__.\n\nFor ______________ Bank\n(Authorised Signatory – Name, Designation, Code No.)",
]

PAAA_FORMAT = [
    "## PERMANENT ALTERNATE ACCOMMODATION AGREEMENT",
    "THIS PERMANENT ALTERNATE ACCOMMODATION AGREEMENT is made at {{exec.place}} on this ____ day of ______________, 20__ BETWEEN {{upper:developer.name}} (the “Developer”) of the FIRST PART; [NAME OF EXISTING MEMBER(S)] (the “Existing Member”) of the SECOND PART; AND {{upper:society.name}} (the “Society”) of the THIRD PART, as Confirming Party.",
    "WHEREAS by a Development Agreement dated ______________ registered under Serial No. ______________ (the “Development Agreement”) the Society appointed the Developer to redevelop the Property described therein, and the Existing Member is the member of the Society in respect of Existing Premises No. [UNIT NO.] admeasuring [EXISTING AREA] square feet RERA carpet area.",
    "1. The Developer shall construct and allot to the Existing Member, free of cost, the Members’ New Premises being Flat No. ______ on the ______ floor of the New Building admeasuring [NEW AREA] square feet RERA carpet area (with balcony / terrace of ______ square feet stated separately), together with [PARKING] parking space(s), with the amenities and specifications set out in the Sixth Schedule to the Development Agreement.",
    "2. The Developer shall pay to the Existing Member the Rent, brokerage, deposit, shifting and re-shifting charges and other amounts set out against the Existing Member’s name in the Fifth Schedule to the Development Agreement, on the dates and in the manner provided therein, and the Rent shall continue until the Possession Date as defined in the Development Agreement.",
    "3. The Existing Member shall vacate the Existing Premises upon receipt of a Vacation Notice issued after fulfilment of the conditions precedent set out in Article XII of the Development Agreement.",
    "4. Possession of the Members’ New Premises shall be delivered only after the Full Occupation Certificate is obtained and the conditions for a Valid Possession Notice under the Development Agreement are fulfilled. The Developer shall rectify defects during the Defect Liability Period.",
    "5. This Agreement is executed in pursuance of, and is incidental to, the Development Agreement, which shall prevail in case of inconsistency save where this Agreement is more beneficial to the Existing Member. The stamp duty and registration charges hereon shall be borne by the Developer; the Parties shall obtain advice on the stamp duty payable under the Maharashtra Stamp Act, 1958 having regard to the stamp duty paid on the Development Agreement.",
    "6. The Existing Member’s rights hereunder are heritable and transferable in accordance with the Development Agreement and the bye-laws of the Society, and shall not be subject to any charge created by the Developer.",
    "IN WITNESS WHEREOF the Parties have signed this Agreement on the day and year first hereinabove written.",
]

VACATION_FORMAT = [
    "## VACATION UNDERTAKING",
    "To,\nThe Secretary, {{society.name}}, {{society.address}}.\nCopy to: {{developer.name}}; {{pmc.name}}.",
    "I / We, [NAME(S)], member(s) of the Society in respect of Existing Premises No. [UNIT NO.], having received the Vacation Notice dated ______________ together with the certificate of the PMC confirming fulfilment of the conditions precedent under Article XII of the Development Agreement dated ______________, hereby confirm that:",
    "(a) I / We have this day vacated the said Existing Premises and handed over its keys to the Society for onward delivery to the Developer under the handover memorandum;",
    "(b) I / We have received the brokerage, shifting charges, refundable deposit and advance Rent stated against my / our name in the Fifth Schedule to the Development Agreement, namely Rs. ______________ (details: ______________);",
    "(c) I / We have cleared the electricity, water and Society dues up to this date (meter reading: ______________);",
    "(d) I / We shall not claim any right in the materials of the Existing Buildings and have removed all my / our belongings.",
    "This undertaking is without prejudice to my / our rights under the Development Agreement and the PAAA, which are not waived in any manner.",
    "Place: ______________\tDate: ______________\n\n(Signature of Member(s))",
]

POA_FORMAT = [
    "## POWER OF ATTORNEY",
    "TO ALL TO WHOM THESE PRESENTS SHALL COME, {{upper:society.name}}, a co-operative housing society registered under the MCS Act bearing Registration No. {{society.reg_no}} (the “Society”), acting through its authorised office-bearers, SENDS GREETINGS.",
    "WHEREAS by a Development Agreement dated ______________ (the “Agreement”) the Society appointed {{developer.name}} (the “Developer”) to redevelop the Property described therein, and agreed to execute this Power of Attorney for the limited purposes set out herein.",
    "NOW KNOW YE ALL AND THESE PRESENTS WITNESS that the Society hereby appoints the Developer, acting through its directors / partners named in the Agreement, as its attorney, to do the following acts in the name and on behalf of the Society, strictly in accordance with the Agreement and at the cost and risk of the Developer:",
    "1. to sign and submit applications, plans (as approved by the Society in accordance with the Agreement), undertakings and indemnities, other than any undertaking creating a liability on the Society, before CIDCO, {{property.authority}} and other Authorities for obtaining the Approvals;",
    "2. to appear before such Authorities and pay fees, premiums and deposits;",
    "3. to apply for and obtain utility connections for the New Building;",
    "4. to execute and register agreements for sale and other documents relating to the Developer’s Free Sale Component only, in which the Society shall not be a party save as required by Applicable Laws;",
    "5. to admit execution of documents relating to the above before the Sub-Registrar of Assurances.",
    "This Power of Attorney does not authorise the attorney to (a) mortgage, charge or encumber the Plot, the Rehabilitation Component or the Common Areas and Amenities; (b) deal with the Members’ New Premises; (c) give any consent or approval on behalf of the Society under the Agreement; (d) sign any document varying the Agreement; or (e) delegate these powers, save to the extent expressly permitted by the Agreement.",
    "This Power of Attorney is co-extensive with the Agreement and shall stand revoked automatically upon termination of the Agreement, without any further act, deed or notice.",
    "IN WITNESS WHEREOF the Society has executed this Power of Attorney on the ____ day of ______________, 20__.",
]

POSSESSION_FORMAT = [
    "## HANDOVER MEMORANDUM, POSSESSION RECEIPT AND INVENTORY",
    "Date and time of handover: ______________\nHandover by: {{society.name}}\nReceived by: {{developer.name}}\nIn the presence of: {{pmc.name}} (PMC)",
    "1. Conditions precedent: The PMC certifies that the conditions precedent under Article XII of the Development Agreement were fulfilled on ______________ (certificate reference: ______________).",
    "2. Premises handed over: All {{num:property.units_count}} Existing Premises / ______ Existing Premises (list of Existing Premises not vacated, if any, to be annexed).",
    "3. Inventory: keys (nos.) ______; electricity meters (nos. and readings) ______; water meters ______; Society records / furniture retained by the Society ______; other ______.",
    "4. Condition of the Property and adjoining structures (photographs annexed): ______________.",
    "5. The Developer acknowledges receipt of possession as licensee for the purposes of the Agreement and not in part performance under Section 53A of the Transfer of Property Act, 1882, and confirms that the Handover Date for the purposes of the Agreement is ______________.",
    "For the Society: ____________\tFor the Developer: ____________\tPMC: ____________",
]

ANNEXURE_FORMATS = {
    "bg_format": BG_FORMAT,
    "paaa": PAAA_FORMAT,
    "vacation_undertaking": VACATION_FORMAT,
    "poa": POA_FORMAT,
    "possession_receipt": POSSESSION_FORMAT,
}
