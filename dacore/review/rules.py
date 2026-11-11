"""Society-protective review rules for Development Agreements drafted by others.

Design principles (Module 2, reasonableness test):
* targeted, minimal amendments that preserve the original drafting, numbering and flow;
* a rule fires only where the clause is actually deficient (guards skip satisfactory clauses);
* amendments never introduce project facts or new figures – where a figure must be agreed the
  amendment uses “[●]” and is marked Negotiable (commercial change identified);
* beneficial provisions already present are never deleted (enforced in reviewer.reasonable()).

action:
    replace       – replace the matched text (group "x" if present, else whole match) with `text`
    append        – add `text` at the end of the paragraph (before the final full stop)
    insert_after  – insert `text` immediately after the matched text
    delete        – delete the matched text
    replace_para  – replace the whole paragraph text (after any manual clause number)
    delete_para   – delete the whole paragraph
    comment       – comment only (negotiation point; no textual change)
"""
from __future__ import annotations

from dataclasses import dataclass, field

A = r"['’]"   # straight or curly apostrophe


@dataclass
class RR:
    id: str
    title: str
    category: str            # Legal | Commercial | Construction | Society Protection
    severity: str            # Critical | High | Medium | Low
    pattern: str             # detection (and edit-anchor) regex, case-insensitive
    action: str
    text: str = ""
    reason: str = ""
    benefit: str = ""
    risk: str = ""
    legal: str = ""
    mandatory: bool = True
    guard: str | None = None          # if this regex matches the paragraph, the clause is satisfactory -> skip
    requires: str | None = None       # paragraph must also match this
    allows_figures: bool = False
    allow_beneficial_delete: bool = False
    library: str = ""


RULES: list[RR] = [
    # ------------------------------------------------------------------ possession / completion
    RR("POS-01", "Deemed possession on failure to take delivery", "Society Protection", "Critical",
       r"it (?:will|shall) be deemed that (?:the )?(?:existing )?members?" + A + r"?s?" + A + r"? allocation (?:is|has been) (?:already )?delivered", "replace",
       "possession shall be treated as delivered only upon the Developer handing over the keys of such premises to the Society after the expiry of the period stipulated in a possession notice issued after obtaining the full Occupation Certificate and completing such premises in all respects",
       "The original clause deems possession to be delivered on a mere failure to take delivery, irrespective of whether the premises are legally and practically ready. That would also stop rent prematurely.",
       "Rent and the Developer's obligations continue until premises that are actually ready are handed over.",
       "Premature cessation of rent; members bound to accept incomplete premises.", "RERA, Sections 11(4)(b), 19(10)", library="Possession and handover"),
    RR("POS-02", "Completion deemed on date of OC application", "Society Protection", "Critical",
       r"In such circumstances,?\s*the date of application for obtaining the Occupanc\w+ Certificate shall be treated as the date of completion(?:[^.]|\.(?=\d))*\.", "delete",
       reason="Treating the date of application for OC as the completion date allows the Developer to stop the completion clock (and LD) without completing the building or obtaining OC.",
       benefit="Completion is measured by the actual grant of the full Occupation Certificate.", risk="Indefinite delay without consequence.", legal="RERA, Section 18"),
    RR("POS-03", "Developer exempt from authority delays in obtaining OC", "Construction", "High",
       r"shall not be held liable for the delay caused on account of the authorities[^.]*?(?=\.)", "insert_after",
       ", save where such delay is attributable to the Developer's failure to apply in time, to comply with the requirements of the authority, or to complete the works in accordance with the sanctioned plans",
       "Delay in OC is very often caused by the Developer's own non-compliance. The exemption must be confined to genuine delays of the authority.",
       "Developer remains responsible for delays caused by its own non-compliance.", "Open-ended extension of completion date.", guard=r"save where|attributable to the Developer"),
    RR("POS-04", "Completion linked to OC 'or its Architect'", "Construction", "High",
       r"\s*or its Architect(?=,)", "delete",
       reason="Only the planning authority can grant an Occupation Certificate; the Developer's own architect's certificate cannot evidence completion.",
       benefit="Completion depends on an independent statutory certificate.", risk="Self-certified completion.", legal="UDCPR; MRTP Act, 1966"),
    RR("POS-05", "Completion on OC without readiness", "Society Protection", "High",
       r"(?<=deemed complete upon receipt of the )Occupancy Certificate \(OC\)", "replace",
       "full Occupancy Certificate (OC) for the entire building (and not a part occupancy certificate), with functional water, electricity and drainage connections, lifts and fire systems and the completion of all agreed amenities",
       "A part OC, or an OC without utilities and amenities, does not make the rehabilitation premises fit for occupation.",
       "Completion requires full OC and actual readiness.", "Members forced into incomplete buildings; rent stops.", "RERA, Sections 11, 19(10)"),
    RR("POS-06", "Deemed taking of possession without readiness", "Society Protection", "Medium",
       r"shall be deemed to have taken possession of the Members" + A + r"? New Premises on the Possession Date", "insert_after",
       ", provided that the Members' New Premises are complete in all respects with functional utility connections and the Possession Notice was issued after receipt of the full occupation certificate",
       "Deemed possession should operate only where the premises are actually ready.", "Protects members against deemed possession of incomplete premises.",
       "Rent cessation and maintenance liability before readiness.", guard=r"complete in all respects|functional utilit"),
    RR("RENT-01", "Rent ceases on mere issuance of OC", "Commercial", "Critical",
       r"(?:until|till|up ?to)\s+(?:the\s+)?(?:issuance|issue|receipt|obtaining|grant)\s+of\s+(?:the\s+)?(?:full\s+)?Occupa\w+\s+Certificate", "replace",
       "until the Developer has obtained the full Occupation Certificate and has offered vacant and peaceful possession of the Members' New Premises together with all functional utility connections, common facilities and agreed amenities, subject to the Society's verification of compliance with the terms of this Agreement",
       "The original clause permits rent to cease merely upon obtaining OC, irrespective of whether the rehabilitation premises are ready for actual occupation. The proposed amendment protects the members against premature cessation of displacement compensation.",
       "Rent continues until ready premises are actually offered.", "Premature cessation of displacement compensation.", "Indian Contract Act, 1872, Section 73",
       requires=r"\brent\b", guard=r"(?:Occupa\w+\s+Certificate)[^.]{0,120}(?:possession|handing over|hand over)"),
    RR("RENT-02", "Developer not liable for rent during society-caused delay", "Commercial", "High",
       r"the Developer shall not be liable for rent or compensation during such period", "replace",
       "the Developer shall not be liable for liquidated damages for such period, but shall continue to pay rent to the members who are not responsible for such delay",
       "Rent is displacement compensation for members who have vacated. Members who are not at fault should not lose rent because of the default of others.",
       "Non-defaulting members continue to receive rent.", "Collective punishment of members.", "Indian Contract Act, 1872, Section 73"),
    RR("RENT-03", "Developer exempt for member non-compliance without rent safeguard", "Commercial", "Medium",
       r"shall not incur any liability for delay caused due to Force Majeure events or default or non-compliance by the Existing Members", "insert_after",
       ", save that the rent and other monetary consideration shall continue to be paid to all members who are not in default",
       "The exemption should not extend to the continuing rent obligation towards members who are not in default.", "Rent continues for non-defaulting members.", "Loss of rent."),
    # ------------------------------------------------------------------ force majeure
    RR("FM-01", "Force majeure affecting Developer 'directly or indirectly'", "Legal", "High",
       r"which may affect the developer directly or indirectly", "replace",
       "which are beyond the reasonable control of the Developer, could not have been prevented by the exercise of reasonable diligence and directly prevent the performance of its obligations, and in respect of which the Developer has given written notice with supporting documents",
       "‘Directly or indirectly’ converts ordinary commercial risk into force majeure. A narrow, objective definition with notice and proof is required.",
       "Only genuine, proven events extend time.", "Indefinite extensions on vague grounds.", "Indian Contract Act, 1872, Sections 32, 56"),
    RR("FM-02", "Material shortage as force majeure", "Legal", "High",
       r"^\s*Non\s*[–-]\s*availability of steel", "append",
       ", only where such non-availability is a direct consequence of an event of force majeure and is not attributable to the Developer's financial condition, commercial decisions or contractors",
       "Shortage or price increase of materials is an ordinary commercial risk of a developer.", "Developer bears ordinary procurement risk.", "Delay excused by market conditions.", guard=r"direct consequence"),
    RR("FM-03", "Change in rules as force majeure", "Legal", "Medium",
       r"^\s*Changes in any rules, regulation", "append",
       ", only to the extent such change prohibits or suspends construction on the said Property, and no such change shall reduce the entitlements of the members or the monetary consideration payable to them",
       "A change in regulations should not reduce members' entitlements and should excuse delay only where it actually stops construction.", "Entitlements protected against regulatory change.", "Reduction of entitlements.", guard=r"shall not reduce"),
    RR("FM-04", "Catch-all force majeure without exclusions", "Legal", "High",
       r"any event beyond the reasonable control of the Developer, and which is unavoidable", "append",
       "; provided that shortage of funds, financial difficulty, market conditions, increase in the price of materials or labour, and defaults of contractors or consultants shall not constitute force majeure",
       "A catch-all clause without exclusions allows ordinary financial difficulties to be pleaded as force majeure.", "Financial difficulties excluded.", "Abuse of force majeure.", guard=r"shortage of funds|financial difficult"),
    RR("FM-05", "Force majeure suspends obligations without preserving rent", "Commercial", "Critical",
       r"shall be excused from the performance or punctual performance of its obligations", "append",
       ". Notwithstanding the foregoing, the obligation of the Developer to pay rent, escalation and all other monetary consideration to the members and the Society shall continue and shall not be suspended or excused by reason of any event of force majeure",
       "Force majeure must not override the continuing payment obligations; members remain displaced during the force majeure period.",
       "Rent continues during force majeure.", "Members left without rent during prolonged events.", requires=r"force majeure", guard=r"\brent\b"),
    RR("FM-06", "Prolonged force majeure – no Society exit", "Society Protection", "Medium",
       r"failing which the dispute shall be resolved in accordance with Dispute resolution clause under this Agreement", "insert_after",
       ", and the Society shall also be entitled to terminate this Agreement by written notice, without either party claiming damages for the force majeure period",
       "If the project is frustrated for a prolonged period, the Society needs a clear right to exit and appoint another developer.", "Clear exit route.", "Society locked in indefinitely."),
    RR("FM-07", "Government authority delays treated as member-caused delays", "Construction", "Medium",
       r"(?<=including but not limited to )government authorities,\s*", "delete",
       reason="Delays of government authorities are not acts of the members; bundling them with member defaults gives the Developer an unconditional full extension.",
       benefit="Authority delays are dealt with only under force majeure with proof.", risk="Automatic extension of completion date."),
    # ------------------------------------------------------------------ termination
    RR("TER-01", "Society cannot terminate until arbitral award", "Society Protection", "Critical",
       r"The Society shall not be entitled to terminate and/or cancel this Agreement[^.]*?till Arbitral Award", "replace_para",
       "The Society shall be entitled to terminate this Agreement, the Specific Power of Attorney and the ancillary documents in accordance with the termination provisions of this Agreement. Such termination shall not be conditional upon any prior arbitral award; any dispute as to the validity of the termination may be referred to arbitration, and the pendency of such proceedings shall not prevent the Society from invoking the bank guarantee or appointing another developer, save as may be ordered by a court or arbitral tribunal of competent jurisdiction.",
       "The original clause disables the Society completely: it cannot terminate until an arbitral award, any termination is void ab initio, and the members become liable to compensate the Developer. This defeats the Society's statutory and contractual remedies.",
       "Society retains an effective termination right; arbitration remains available for disputes.", "Society unable to replace a defaulting developer for years.",
       "Indian Contract Act, 1872, Sections 39, 73; Arbitration and Conciliation Act, 1996, Section 9", allow_beneficial_delete=True, library="Comprehensive termination grounds"),
    RR("TER-02", "Termination only for non-payment of rent", "Society Protection", "Critical",
       r"solely on the ground of failure by the Developer to pay monthly rent", "replace",
       "on the ground of (i) failure by the Developer to pay monthly rent",
       "Limiting termination to non-payment of rent leaves the Society without remedy for non-completion, abandonment, insolvency, failure to furnish the bank guarantee or unauthorised assignment.",
       "Termination available for all material Developer defaults.", "Society bound to a non-performing developer.", "Indian Contract Act, 1872, Section 39"),
    RR("TER-02b", "Additional termination grounds", "Society Protection", "Critical",
       r"(?<=for a continuous period of 2 \(two\) consecutive calendar months)", "insert_after",
       "; or (ii) failure to obtain the approvals or to complete the project within the timelines (including grace period) set out in this Agreement; or (iii) failure to furnish, renew or replenish the bank guarantee; or (iv) abandonment or suspension of the work for a continuous period of [●] months; or (v) insolvency, winding up or admission of insolvency proceedings against the Developer; or (vi) assignment, change of control or encumbrance in breach of this Agreement; or (vii) any other material breach of this Agreement not cured within the cure period",
       "Complements TER-02 with the standard Developer events of default.", "Comprehensive grounds.", "No remedy for serious defaults.", allows_figures=True, mandatory=True),
    RR("TER-08", "'Sole ground' heading for termination", "Society Protection", "Medium",
       r"Sole Ground for Termination Process and Mandatory Procedure", "replace", "Grounds for Termination and Procedure",
       "Consequential to the widening of the termination grounds.", "Consistency.", "Heading contradicts amended grounds."),
    RR("TER-09", "Termination only 'through arbitration'", "Society Protection", "Critical",
       r"initiate the termination process through arbitration under this Agreement", "replace", "terminate this Agreement in accordance with the procedure set out below",
       "Termination must be a right exercisable by notice after cure, not a remedy obtainable only through an arbitral award.", "Effective termination right.", "Termination delayed for years.", "Arbitration and Conciliation Act, 1996"),
    RR("TER-10", "Society must invoke arbitration instead of terminating", "Society Protection", "Critical",
       r"the Society shall invoke arbitration in accordance with Article XIV of this Agreement\.\s*The question whether the explanation(?:[^.]|\.(?=\d))*\.", "replace",
       "the Society may, after obtaining the written opinion of its PMC and Legal Advisor and the approval of its general body, terminate this Agreement by written notice, and any dispute regarding such termination may be referred to arbitration in accordance with Article XIV of this Agreement.",
       "Requiring an arbitral finding on the adequacy of the Developer's explanation before termination disables the Society for the duration of the arbitration.", "Society can act after cure period.", "Prolonged default without remedy."),
    RR("TER-03", "Termination right described as 'specific and limited'", "Society Protection", "Medium",
       r"specific and limited procedure", "replace", "procedure",
       "Consequential to the widening of the termination grounds.", "Consistency with amended termination clause.", "Internal inconsistency."),
    RR("TER-04", "Other breaches restricted to specific performance", "Society Protection", "High",
       r"which is exclusively governed by the termination procedure", "replace", "which is governed by the termination procedure",
       "Other material breaches (inferior materials, plan deviations, safety violations) must also allow termination after cure, not only specific performance.",
       "Society may terminate for other material breaches after cure.", "Society limited to specific performance suits."),
    RR("TER-05", "No termination or interference pending award", "Society Protection", "Critical",
       r"It is further agreed that pending the pronouncement of such decision or award(?:[^.]|\.(?=\d))*\.", "replace",
       "The pendency of arbitration shall not prevent the Society from invoking the bank guarantee or from seeking interim relief under Section 9 of the Arbitration and Conciliation Act, 1996.",
       "The clause bars the Society from any action while the Developer continues work, making arbitration a tool to prolong default.",
       "Interim protection preserved.", "Society disabled during long arbitrations.", "Arbitration and Conciliation Act, 1996, Section 9"),
    RR("TER-06", "Automatic refund of all developer investment on termination", "Society Protection", "Critical",
       r"In the event of termination of this Agreement, whether pursuant to a mutual decision of the parties, an arbitral award or any other circumstance", "replace_para",
       "In the event of termination of this Agreement, the consequences shall depend upon the cause of termination. Where this Agreement is terminated on account of the default of the Developer, the Society shall be entitled to invoke the bank guarantee, appoint a new developer and recover its losses, and the Developer shall be entitled only to such amount, if any, as the Society actually receives from the new developer specifically towards the value of the work executed by the Developer as certified by the PMC, after deduction of all losses, damages and costs of the Society and its members. Where this Agreement is terminated on account of the default of the Society, the Developer shall be entitled to the refund of amounts actually paid to the Society under this Agreement, as may be determined in accordance with the dispute resolution provisions. No amount shall be recoverable from individual members save to the extent of payments received by them in excess of their entitlements.",
       "The original clause obliges the Society and members to refund every payment and all developer expenditure irrespective of the reason for termination, and bars appointment of a new developer until such refund – effectively a lock-in that makes termination impossible.",
       "Fault-based consequences; Society can appoint a new developer.", "Society financially unable to exit even for developer default.",
       "Indian Contract Act, 1872, Sections 65, 73, 74", allow_beneficial_delete=True, library="No automatic reimbursement on termination"),
    RR("TER-07", "Cure conditional on breach being 'non disputable'", "Society Protection", "High",
       r",?\s*which is non disputable by either parties", "delete",
       reason="Any developer can dispute a breach; making the termination process available only for ‘non-disputable’ breaches nullifies it.",
       benefit="Termination process not defeated by a mere dispute.", risk="Illusory termination right."),
    # ------------------------------------------------------------------ security
    RR("BG-01", "Bank guarantee furnished after vacation", "Society Protection", "Critical",
       r"(?<=submitted )on peaceful handover of 100% units of the existing members along with the society plot", "replace",
       "before the issuance of the vacation notice and before the members are called upon to vacate the existing premises",
       "If the guarantee is furnished only after vacation, the members vacate without security. The BG must be a condition precedent to vacation.",
       "Security in place before members give up possession.", "Members displaced without security.", library="Bank Guarantee – timing and nature"),
    RR("BG-02", "BG release on Developer's own architect certificate", "Society Protection", "High",
       r"stage completion certificate by the Project Architect of the Developers", "insert_after",
       " and verified and certified in writing by the Society's PMC",
       "Release of security must not depend on the Developer's own consultant.", "Independent verification of milestones.", "Premature release of security.",
       guard=r"\bPMC\b"),
    RR("BG-03", "Long notice before BG encashment", "Society Protection", "Medium",
       r"advanced 60 days\s+notice", "comment",
       reason="A 60-day notice period before encashment defeats the on-demand nature of the guarantee and allows the Developer to approach court for an injunction. Suggest 15 days. (Negotiable – commercial term.)",
       benefit="Effective security.", risk="Injunction against invocation.", mandatory=False),
    RR("BG-04", "No BG tranche retained during defect liability period", "Construction", "Medium",
       r"^\s*50% on Receiving Occupation Certificate", "comment",
       reason="The entire guarantee is released at OC. A tranche should be retained until expiry of the defect liability period to secure rectification of defects. (Negotiable.)",
       benefit="Security for DLP obligations.", risk="No security for defects.", mandatory=False),
    RR("BG-05", "Vacation before Commencement Certificate", "Society Protection", "Critical",
       r"after getting unhindered and peaceful possession of the entire plot from the Society along with handover of all the\s*_*\s*units of the existing members", "replace",
       "after having obtained the approval of plans and, before the members are called upon to vacate, the Developer shall have obtained the Commencement Certificate, furnished the bank guarantee, executed and registered the permanent alternate accommodation agreements and paid the amounts payable to the members on vacation",
       "The members must not vacate before the Commencement Certificate, bank guarantee, PAAA registration and initial payments. Vacating first exposes them to indefinite displacement if the Developer fails to obtain approvals.",
       "Sequential conditions precedent to vacation.", "Members vacate with no approvals in hand.", "79A Directions (verify current wording)", library="Sequential conditions precedent to vacation"),
    RR("FIN-01", "Unrestricted mortgage by Developer", "Society Protection", "Critical",
       r"Developer shall be entitled to (?:raise finance|create (?:a )?(?:charge|mortgage)|mortgage)", "append",
       "; provided that the Developer shall not create any mortgage, charge or encumbrance over the plot, the Society's leasehold rights, the premises to be allotted to the members or the common areas, and every lender shall have recourse only to the Developer's free sale component and its receivables",
       "The clause permits financing without excluding the rehabilitation premises and the plot.", "Members' entitlements protected from lenders.", "Enforcement by lenders against members' flats.",
       guard=r"exclud|shall not be entitled to create|shall not mortgage|will not mortgage|except|save and except"),
    # ------------------------------------------------------------------ delay
    RR("DEL-01", "Parties to ‘fix a new timeline’ after delay", "Society Protection", "Critical",
       r"then the parties shall fix a new timeline for completion of project\.", "replace",
       "then, without prejudice to the Society's right to terminate this Agreement and invoke the bank guarantee, the Developer shall continue to pay rent and the liquidated damages provided herein until completion.",
       "An agreement to agree on a new timeline leaves no enforceable completion date after the grace period.", "Enforceable long-stop consequence.", "Indefinite delay.", "Indian Contract Act, 1872, Section 29"),
    RR("DEL-02", "Grace period ‘at the discretion’", "Construction", "Medium",
       r"to complete the project at the discretion\.", "replace",
       "to complete the project, subject to the Developer continuing to pay rent and all other amounts payable under this Agreement during the grace period.",
       "The grace period should be conditional on continued payment of rent.", "Rent continues in grace period.", "Ambiguity."),
    RR("DEL-03", "Developer obligations expressed as ‘endeavour’", "Construction", "Medium",
       r"(?<=Developer )(?:shall|will) endeavou?r to ", "replace", "shall ",
       "‘Endeavour’ converts a firm obligation into a best-efforts promise and makes timelines unenforceable.", "Firm obligations.", "Unenforceable timelines."),
    RR("DEL-04", "LD only if delay 'solely' attributable to Developer", "Commercial", "High",
       r"due to reasons attributable solely to the Developer", "replace", "due to reasons not attributable to the Society or its members",
       "‘Solely’ allows the Developer to avoid liquidated damages by pointing to any contributing cause.", "LD applies unless the Society caused the delay.", "Liquidated damages rarely payable.", "Indian Contract Act, 1872, Section 74"),
    # ------------------------------------------------------------------ members
    RR("MEM-01", "Per-day penalty with high interest on members", "Society Protection", "High",
       r"the Developer shall be entitled to levy a penalty of Rs\.?\s*[\d,]+/?-?\s*\([^)]*\)\s*per day(?:[^.]|\.(?=\d))*\.\s*(?:till the date(?:[^.]|\.(?=\d))*\.)?", "replace",
       "the Society and the Developer shall be entitled to take the steps provided in this Agreement to secure vacant possession from such member, and the Developer shall be entitled to recover from such member the reasonable and documented costs incurred by reason of such delay.",
       "A per-day penalty with 24% interest on individual members is likely to be treated as a penalty (not a genuine pre-estimate of loss) and is coercive. Proportionate, documented cost recovery is enforceable and adequate.",
       "Members protected from punitive penalties; Developer still recovers actual costs.", "Unenforceable penalty; disputes with members.", "Indian Contract Act, 1872, Section 74"),
    RR("MEM-02", "Punitive liquidated damages on non-consenting members", "Society Protection", "Medium",
       r"an amount equivalent to 100% of\s+the Corpus Fund of such Member, for every month of delay", "comment",
       reason="Forfeiture of the entire corpus share for every month of delay, plus 6 months' rent and 18% interest, is likely to be regarded as a penalty. Recommend limiting recovery to documented costs and suspension of rent for the delay period. (Negotiable.)",
       benefit="Proportionate remedy.", risk="Unenforceable penalty; dissent among members.", mandatory=False),
    RR("MEM-03", "Developer's right of first refusal on member transfers", "Society Protection", "Medium",
       r"right of first refusal", "comment",
       reason="A developer right of first refusal / matching right restricts the members' right to transfer and is not required for redevelopment; transfers should be regulated by the Society's bye-laws and a deed of adherence. (Negotiable.)",
       benefit="Members' transfer rights preserved.", risk="Restriction on alienation.", mandatory=False, legal="Transfer of Property Act, 1882, Section 10"),
    RR("MEM-04", "Bar on any sale of existing premises", "Society Protection", "Medium",
       r"none of the existing premises shall be sold", "comment",
       reason="An absolute bar on transfer after the DA is a restraint on alienation. Transfers with Society approval and a deed of adherence protect the project equally well. (Negotiable.)",
       benefit="Members' statutory rights preserved.", risk="Possibly void restraint.", mandatory=False, legal="Transfer of Property Act, 1882, Section 10"),
    # ------------------------------------------------------------------ developer discretion / plans
    RR("DIS-01", "Developer may substitute amenities unilaterally", "Construction", "High",
       r"The Developer reserves the right to substitute or modify the amenities or facilities", "replace",
       "The Developer may, with the prior written consent of the Society, substitute or modify the amenities or facilities",
       "Unilateral substitution of amenities erodes the tender commitments.", "Society approval for any substitution.", "Reduction in specifications."),
    RR("DIS-02", "Free-sale modifications on information only", "Legal", "Medium",
       r"As far as modification or amendment to the Free Sale Area is concerned only information will be provided to the Society", "insert_after",
       ", provided that such modification complies with Section 14 of RERA and does not affect the members' premises, the common areas, the amenities or the structural design of the building",
       "Free-sale changes can affect common areas, structure and services shared with members.", "Members' interests insulated from free-sale changes.", "Indirect impact on rehabilitation component.", "RERA, Section 14"),
    RR("DIS-03", "Exclusive and unfettered design rights", "Construction", "High",
       r"exclusive and unfettered right to determine", "replace",
       "right, subject to the sanctioned plans, Applicable Laws (including Section 14 of RERA) and the prior approval of the Society wherever the members' premises, the common areas, the amenities or the structural design are affected, to determine",
       "Unfettered rights over height, floors, plinth and layout inevitably affect the rehabilitation component and common areas.", "Society approval for changes affecting members.", "Unilateral redesign.", "RERA, Section 14"),
    RR("DIS-04", "Society to abide by Developer's decisions on PAA", "Society Protection", "High",
       r"agrees to\s+abide by the Developer" + A + r"s decision with respect to", "replace",
       "shall be consulted, and the prior approval of the Society in a general body meeting shall be obtained by the Developer, with respect to",
       "The location, shape and amenities of the permanent alternate accommodation are core member entitlements and require Society approval.", "Member approval of rehab design.", "Members bound by unilateral decisions."),
    RR("DIS-05", "Decisions 'without any restrictions'", "Society Protection", "High",
       r"shall allow for such changes without any restrictions", "replace", "shall allow for such changes, subject to the approval of the Society in a general body meeting where such changes affect the Society or its members,",
       "An unrestricted authority to change the development plan contradicts the requirement of Society approval for changes affecting members.", "Consistency and control.", "Unilateral changes."),
    RR("DIS-06", "Unrestricted exploitation of FSI 'as per Developer’s own sole discretion'", "Legal", "High",
       r",?\s*as per Developer" + A + r"s own sole discretion, without requiring any consent, concurrence, approval or No Objection from the Society or its existing members, and without any type of objection or demands from the Society or its existing members", "delete",
       reason="This contradicts the clause requiring the Society's consent for use of increased FSI, and would let the Developer appropriate future FSI benefits without sharing.",
       benefit="Consistency with the Future FSI sharing clause.", risk="Loss of future FSI benefit.", legal="79A Directions"),
    RR("DIS-07", "Purchaser agreements binding on Society", "Legal", "High",
       r"shall be valid and binding on the Society and its existing members", "replace",
       "shall be binding on the Society only insofar as they are consistent with this Agreement, and the Society and its existing members shall not be liable under any such agreement",
       "The Developer's independent sales must not create liabilities for the Society.", "Society insulated from purchaser claims.", "Society liable for developer's contracts.", "RERA, Sections 11, 18"),
    RR("DIS-08", "Signage rights in perpetuity", "Commercial", "Low",
       r"provided to the Developer in perpetuity", "replace", "provided to the Developer for a period of [●] years from the receipt of the full occupation certificate",
       "Perpetual signage rights on the Society's building are an encumbrance on the Society's common areas. (Negotiable – figure to be agreed.)", "Time-bound right.", "Perpetual encumbrance.",
       allows_figures=True, mandatory=False),
    # ------------------------------------------------------------------ indemnity / liability
    RR("IND-01", "Developer indemnity only for 'solely' negligent acts", "Society Protection", "High",
       r"caused solely by the negligent", "replace", "caused by the negligent",
       "‘Solely’ allows the Developer to escape liability whenever any other factor contributed.", "Effective indemnity.", "Illusory indemnity.", "Indian Contract Act, 1872, Section 124"),
    RR("IND-02", "Developer indemnity ends at handover", "Society Protection", "High",
       r"and only until handover of possession of the permanent alternate accommodation to the Existing Members", "replace",
       "and until the expiry of the defect liability period",
       "Construction-related claims frequently arise after handover; the indemnity should run at least through the defect liability period.", "Indemnity through DLP.", "Uncovered post-handover claims."),
    RR("IND-03", "Cap on Developer's aggregate liability", "Society Protection", "Critical",
       r"The aggregate liability of the Developer under this Clause shall not exce\w*(?:[^.]|\.(?=\d))*\.", "delete",
       reason="A cap on the Developer's indemnity for injury, death and property damage caused by its construction is unacceptable and may defeat statutory liability.",
       benefit="Full recovery for construction-related claims.", risk="Society bears excess liability.", legal="Indian Contract Act, 1872, Sections 124-125"),
    RR("IND-04", "Society indemnity covers loss of profit and holding costs", "Society Protection", "High",
       r"provided however that any loss of profit or revenue, holding costs(?:[^.]|\.(?=\d))*\.", "replace",
       "provided however that the indemnity of the Society and the members shall be limited to direct losses actually suffered and shall not extend to loss of profit, revenue, holding costs or other indirect or consequential losses.",
       "The Society should not underwrite the Developer's commercial losses; consequential losses are excluded for both parties.", "Society's exposure limited.", "Unlimited Society liability."),
    RR("IND-05", "Society indemnifies title defects investigated by Developer", "Society Protection", "High",
       r"defect in title of the Society to the Property as investigated by the Developer", "replace",
       "any defect in title of the Society to the Property which was not disclosed to the Developer and could not have been discovered by the Developer on reasonable investigation",
       "The Developer has investigated title; the Society should indemnify only for undisclosed defects.", "Indemnity limited to undisclosed defects.", "Society liable for disclosed matters."),
    RR("IND-06", "Society indemnity for CIDCO NOC conformity", "Society Protection", "High",
       r"The Society shall further indemnify the Developer from any monetary liabilities arising at any time with respect to the conformity of the CIDCO" + A + r"s NOC towards the Redevelopment of the project\.", "replace_para",
       "All premiums, charges and conditions of the CIDCO no-objection certificate for the redevelopment shall be borne by and complied with by the Developer, save for any lease rent or dues relating to the period prior to the date of this Agreement, which shall be borne by the Society.",
       "Obtaining and complying with the CIDCO NOC is the Developer's obligation at its cost; an open-ended Society indemnity contradicts this.", "Correct allocation of CIDCO costs.", "Society liable for CIDCO premiums."),
    RR("IND-07", "Developer not liable for Society losses (limitation of liability)", "Society Protection", "Critical",
       r"The Developer shall not be directly or indirectly liable or accountable under this Agreement", "delete_para",
       reason="This limitation contradicts the subsequent sub-clauses which keep the Developer fully liable for breach, delay, negligence and defects. Retaining it would create an internal conflict exploitable by the Developer.",
       benefit="Removes internal contradiction; Developer remains liable.", risk="Developer escapes liability.", allow_beneficial_delete=True),
    RR("REP-01", "Developer may rely on any direction of a single representative", "Society Protection", "High",
       r"The Developer shall have no duty or obligation to inquire as to the authority(?:[^.]|\.(?=\d))*\.", "replace",
       "The Developer shall act only upon communications in writing signed by at least two of the Society's Representatives and, where this Agreement requires the approval of the general body, upon a certified copy of the resolution of the general body; no oral or informal communication shall bind the Society.",
       "Allowing reliance on any direction of an office-bearer exposes the Society to unauthorised consents.", "Only authorised written consents bind the Society.", "Unauthorised consents.", "MCS Act and bye-laws"),
    RR("AMD-01", "Amendment by minutes of meetings", "Legal", "High",
       r"Amendment may be made in the periodical meetings(?:[^.]|\.(?=\d))*\.\s*Such amendments shall be binding(?:[^.]|\.(?=\d))*\.", "replace",
       "No amendment shall be made by minutes of meetings or correspondence; any amendment shall require the approval of the general body of the Society and shall be recorded in a supplemental agreement.",
       "Amendments by minutes signed by committee members bypass the general body and the 79A process.", "General body control over amendments.", "Informal erosion of terms."),
    RR("RERA-01", "Society solely responsible for RERA delay liabilities", "Society Protection", "High",
       r"then in that event the Society shall be held solely responsible for all RERA liabilities(?:[^.]|\.(?=\d))*\.", "replace",
       "then the Society shall be responsible only to the extent that such delay is caused by litigation initiated by the Society or its members or by a defect in title not disclosed to the Developer, and the Developer shall remain responsible for all other liabilities under RERA.",
       "The Society cannot be made the insurer of the Developer's RERA obligations for all litigation, including litigation caused by the Developer.", "Fair allocation.", "Society bears purchasers' RERA claims."),
    RR("LIC-01", "Irrevocable licence that cannot be revoked by the Society", "Society Protection", "Critical",
       r"No action by the Society or any of its existing members shall have the effect of revoking, suspending or limiting this licence, and any such purported action shall be void ab initio\.", "replace",
       "This licence shall be co-terminus with this Agreement and shall stand revoked upon termination of this Agreement in accordance with its terms.",
       "An irrevocable licence surviving termination prevents the Society from recovering the site and appointing another developer.", "Site recoverable on termination.", "Developer remains on site after termination.", "Indian Easements Act, 1882, Sections 60-61"),
    RR("LIC-02", "Licence described as irrevocable, absolute and unconditional", "Society Protection", "High",
       r"irrevocable, absolute and unconditional licence", "replace", "licence",
       "Consequential to LIC-01.", "Consistency.", "Irrevocable licence."),
    RR("DLP-01", "Defect liability void upon member alterations", "Construction", "High",
       r"the defect liability period shall automatically become void\.", "replace",
       "the Developer shall not be liable for defects to the extent directly caused by such works, but the defect liability period shall otherwise continue to apply.",
       "Voiding the entire defect liability for any alteration defeats the statutory 5-year protection under Section 14(3) of RERA.", "Statutory DLP preserved.", "Loss of DLP.", "RERA, Section 14(3)"),
    RR("DLP-02", "Narrow definition of defect", "Construction", "Medium",
       r"caused on account of neglect on the part of the Developer", "replace",
       "and any structural defect or defect in quality, materials or provision of services",
       "Limiting defects to ‘neglect’ requires the members to prove negligence; RERA imposes liability for structural and workmanship defects without proof of neglect.", "Statutory standard.", "Defects excluded.", "RERA, Section 14(3)"),
    RR("DLP-03", "Exclusion of 'vagaries of nature' and hairline cracks", "Construction", "Low",
       r"vagaries of nature, minor hairline cracks on the external and internal walls", "replace",
       "hairline cracks within accepted engineering tolerances as certified by the PMC",
       "‘Vagaries of nature’ would exclude seepage and leakage, which are the most common defects.", "Waterproofing defects covered.", "Seepage claims excluded."),
]


# ------------------------------------------------------------------ missing clauses (document-level)
@dataclass
class MC:
    id: str
    title: str
    severity: str
    present: str               # regex; if found anywhere, clause considered present
    anchor: str                # regex; insert after the LAST paragraph matching this (fallback: before IN WITNESS)
    text: str                  # uses {M} members term, {NP} new premises term, {OC} OC term
    reason: str
    benefit: str
    risk: str
    legal: str = ""
    mandatory: bool = True


MISSING: list[MC] = [
    MC("MC-01", "Bank guarantee as security", "Critical", r"bank guarantee", r"article:CONSIDERATION|COMPENSATION|MONETARY|ENTITLEMENT",
       "As security for the performance of its obligations, the Developer shall, before the {M} are called upon to vacate, furnish to the Society an unconditional, irrevocable and on-demand bank guarantee of a scheduled commercial bank for an amount of Rs. [●], valid until the expiry of the defect liability period and released in stages only upon certification by the PMC.",
       "The draft contains no performance security.", "Security before vacation.", "No security against developer default."),
    MC("MC-02", "Conditions precedent to vacation", "Critical", r"condition[s]? precedent|before (?:the )?(?:members|existing members) (?:are called upon to )?vacate", r"article:VACAT|SOCIETY.{0,30}(?:OBLIGATION|RESPONSIBILIT)|OBLIGATION.{0,25}SOCIETY|APPROVAL",
       "The {M} shall not be required to vacate the existing premises unless the Developer has (a) obtained the approval of plans and the Commencement Certificate; (b) furnished the bank guarantee; (c) executed and registered the permanent alternate accommodation agreements; and (d) paid the brokerage, shifting charges, deposit and advance rent payable on vacation, and the PMC has certified such fulfilment in writing.",
       "Vacation is not sequenced after approvals and security.", "Members vacate only when protected.", "Indefinite displacement."),
    MC("MC-03", "Long-stop date and Society's right to appoint new developer", "Critical", r"appoint (?:a |another |any other |new )+developer|long[- ]stop", r"article:TERMINATION",
       "If the {OC} is not obtained within [●] months after the expiry of the completion period (including the grace period), the Society shall be entitled, without prejudice to its other rights, to terminate this Agreement, invoke the bank guarantee and appoint another developer to complete the project.",
       "No long-stop date or replacement-developer right.", "Exit from a stalled project.", "Project stalled indefinitely."),
    MC("MC-04", "Bar on assignment and change of control", "High", r"(?:Developer shall not|Developers? (?:are|is) not (?:entitled|permitted) to) (?:assign|transfer)|change (?:in|of) (?:the )?(?:control|shareholding|constitution)", r"article:MISCELLANEOUS|ASSIGN",
       "The Developer shall not assign or transfer this Agreement or the development rights, or any part thereof, or bring about a change in its control or shareholding whereby its present promoters cease to control it, without the prior written approval of the Society in a general body meeting.",
       "The draft does not restrict assignment by the Developer.", "Society chooses who develops.", "Project passed to an unknown entity."),
    MC("MC-05", "Construction and third-party insurance", "High", r"insurance", r"article:DEVELOPER.{0,40}(?:OBLIGATION|COVENANT)",
       "The Developer shall, from the date of handover until possession of the {NP}, maintain a contractor's all-risk policy, third-party liability insurance and workmen's compensation insurance with a reputed insurer, and furnish copies of the policies to the Society.",
       "No insurance obligations.", "Insured construction risks.", "Uninsured accidents and damage."),
    MC("MC-06", "Quality assurance, third-party testing and PMC inspection", "High", r"third[- ]party test|NABL|quality assurance", r"article:QUALITY|DEVELOPER.{0,40}(?:OBLIGATION|COVENANT)",
       "The Developer shall implement a quality assurance plan approved by the PMC, get concrete, steel and other materials tested at a NABL-accredited laboratory and furnish the reports to the PMC monthly, and permit the PMC to inspect the works at all reasonable times.",
       "No independent quality control.", "Verified quality.", "Sub-standard construction."),
    MC("MC-07", "Carpet area shortfall compensation", "High", r"short ?fall|deficien\w+ (?:in|of) (?:the )?(?:rera )?carpet|less than the (?:agreed )?carpet", r"article:ENTITLEMENT|COMPENSATION|PERMANENT",
       "Upon completion, the carpet area of each of the {NP} shall be jointly measured by the Developer's architect and the PMC, and if it is less than the agreed carpet area, the Developer shall compensate the concerned member for the shortfall at the prevailing sale rate in the project or the ready reckoner rate, whichever is higher.",
       "No remedy for shortfall in carpet area.", "Members receive the full agreed area.", "Unremedied shortfall."),
    MC("MC-08", "Monthly progress reports", "Medium", r"progress report", r"article:COMPLETION|COMMENCEMENT",
       "The Developer shall furnish to the Society monthly progress reports with photographs, the status of approvals, the payments made to the {M} and the construction programme.",
       "No reporting obligation.", "Transparency.", "Society unaware of slippage."),
    MC("MC-09", "Interest on delayed rent", "Medium", r"interest[^.]{0,80}(?:delay|late)[^.]{0,80}rent|rent[^.]{0,120}interest", r"article:CONSIDERATION|COMPENSATION|MONETARY|ENTITLEMENT",
       "If any instalment of rent is not paid within [●] days of its due date, the Developer shall pay interest at the rate of [●] per cent per annum on the delayed amount until payment, without prejudice to the other rights of the Society.",
       "No consequence for late rent.", "Timely rent.", "Chronic late payment."),
    MC("MC-10", "Society's right to rectify defects at Developer's cost", "Medium", r"rectif\w+[^.]{0,120}(?:recover|reimburs)", r"article:DEFECT|QUALITY",
       "If the Developer fails to rectify a notified defect within [●] days, the Society may get the defect rectified through another agency and recover the cost from the Developer or from the bank guarantee.",
       "No self-help remedy for defects.", "Defects actually get fixed.", "Defects remain unrectified."),
    MC("MC-11", "Survival of indemnities", "Low", r"surviv", r"article:INDEMN",
       "The indemnities given by the Developer shall survive the completion and termination of this Agreement.",
       "Survival not expressly provided.", "Continuing protection.", "Indemnity lapses."),
    MC("MC-12", "No waiver by informal conduct", "Low", r"waive", r"article:MISCELLANEOUS",
       "No failure or delay by the Society in exercising any right shall operate as a waiver, and no waiver shall be effective unless in writing and approved by the general body of the Society; oral or electronic communications and acceptance of payments shall not constitute waiver.",
       "No non-waiver protection.", "Rights preserved despite indulgence.", "Implied waiver."),
    MC("MC-13", "Rent to continue during force majeure", "High", r"(?:force majeure)[^.]{0,300}(?:rent)[^.]{0,80}(?:continu|not be suspended|irrespective)|(?:rent)[^.]{0,200}(?:irrespective of|notwithstanding)[^.]{0,40}force majeure", r"article:FORCE MAJEURE|COMPLETION",
       "Notwithstanding anything contained in this Agreement, the obligation of the Developer to pay rent and other monetary consideration to the {M} shall continue during any event of force majeure.",
       "Force majeure may suspend rent.", "Rent continues.", "Members without rent."),
    MC("MC-14", "No mortgage of members' premises / plot", "Critical", r"(?:shall|will) not (?:be entitled to )?(?:mortgage|create)[^.]{0,120}(?:members|existing members|society|plot|land|rehab)|excluding existing member", r"article:DEVELOPER.{0,40}(?:RIGHT|OBLIGATION|ENTITLEMENT|COVENANT)",
       "The Developer shall not mortgage, charge or encumber the plot, the Society's leasehold rights, the {NP} or the common areas, and lenders of the Developer shall have recourse only to the Developer's free sale component and its receivables.",
       "Rehabilitation premises not protected from developer financing.", "Members' flats protected.", "Lender enforcement against members."),
]


def detect_terms(full_text: str) -> dict[str, str]:
    import re
    def pick(cands, default):
        best, n = default, 0
        for c in cands:
            k = len(re.findall(re.escape(c), full_text))
            if k > n:
                best, n = c, k
        return best
    return {
        "M": pick(["Existing Members", "existing members", "Society Members", "Members", "members"], "members"),
        "NP": pick(["Members’ New Premises", "Members New Premises", "Members' New Premises", "existing members’ allocation", "Existing Members’ Allocation",
                    "Permanent Alternate Accommodation", "Members New Flats"], "new premises to be allotted to the members"),
        "OC": pick(["Occupancy Certificate", "Occupation Certificate", "occupation certificate"], "occupation certificate"),
    }
