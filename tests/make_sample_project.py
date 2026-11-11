"""Create a SIMULATED redevelopment project (fictitious society, developer and members) for testing.

Deliberate test conditions:
* the Lease Deed states plot area 2,150.50 sq. m. but the architect's area statement says 2,105.00 sq. m. (conflict);
* the registration certificate is an image (OCR path);
* the member register has 24 units held by 22 living members: one joint unit, one member holding two units,
  one deceased holder, mortgaged units and areas in sq. m. (unit conversion).
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pymupdf as fitz
import openpyxl
from docx import Document
from PIL import Image, ImageDraw, ImageFont

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "sample_project")
OUT.mkdir(parents=True, exist_ok=True)
SOC = "Sagar Darshan Co-operative Housing Society Ltd."
DEV = "Shubharambh Realty Pvt. Ltd."


def pdf(name, paras):
    d = fitz.open()
    page = d.new_page(width=595, height=842)
    y = 60
    for p in paras:
        rect = fitz.Rect(50, y, 545, y + 400)
        h = page.insert_textbox(rect, p, fontsize=10.5, fontname="helv")
        used = 400 - h if h > 0 else 400
        y += used + 12
        if y > 760:
            page = d.new_page(width=595, height=842); y = 60
    d.save(OUT / name)


def docx(name, paras):
    d = Document()
    for p in paras:
        d.add_paragraph(p)
    d.save(OUT / name)


pdf("Lease_Deed_CIDCO.pdf", [
    "DEED OF LEASE",
    f"THIS DEED OF LEASE is made at Navi Mumbai on 14th March, 2001 between the City and Industrial Development Corporation of Maharashtra Limited (CIDCO), the Lessor, and {SOC}, the Lessee.",
    "The Lessor hereby demises unto the Lessee all that piece of land bearing Plot No. 14, Sector 17, Nerul, Navi Mumbai admeasuring 2,150.50 sq. mtrs. together with the building constructed thereon comprising 24 flats, for a term of 60 (Sixty) years commencing from 01/04/1998.",
    "The said plot is bounded as follows: On or towards the North: 15 m wide road; On or towards the South: Plot No. 15; On or towards the East: Plot No. 13; On or towards the West: Open space / garden.",
    "This Deed has been registered with the Sub-Registrar of Assurances, Thane-9 under Serial No. TNN9-01234-2001.",
])
pdf("Architect_Area_Statement.pdf", [
    "AREA STATEMENT AND FEASIBILITY – PROPOSED REDEVELOPMENT",
    f"Society: {SOC}, Plot No. 14, Sector 17, Nerul.",
    "Plot area as per site measurement: admeasuring 2,105.00 sq. m.",
    "Total development potential: 6,947.00 sq. m. including premium and ancillary FSI under UDCPR 2020.",
    "The existing building of Ground + 3 floors comprising 24 flats was constructed in 1997.",
])
# registration certificate as an image (OCR)
img = Image.new("RGB", (1400, 700), "white")
dr = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("arial.ttf", 34); fb = ImageFont.truetype("arialbd.ttf", 44)
except OSError:
    font = fb = ImageFont.load_default()
lines = [("CERTIFICATE OF REGISTRATION", fb), ("Maharashtra Co-operative Societies Act, 1960", font),
         (f"This is to certify that {SOC}", font), ("Plot No. 14, Sector 17, Nerul, Navi Mumbai", font),
         ("has been registered under the said Act on 12/08/1998", font), ("Registration No. NBOM/CIDCO/HSG/(TC)/1234/1998-99", font)]
y = 60
for t, f in lines:
    dr.text((80, y), t, fill="black", font=f); y += 90
img.save(OUT / "Society_Registration_Certificate.png")

docx("SGBM_Minutes_Selection.docx", [
    "MINUTES OF THE SPECIAL GENERAL BODY MEETING",
    f"{SOC} – Plot No. 14, Sector 17, Nerul, Navi Mumbai.",
    "At the special general body meeting held on 10th January, 2025 the members unanimously resolved to undertake redevelopment of the society building in accordance with the directions under Section 79A.",
    "Chairman: Shri Prakash Ramdas Kulkarni",
    "Secretary: Smt. Meera Anil Joshi",
    "Treasurer: Shri Vinod Shankar Patil",
    "The Society appointed M/s. Sankalp Project Management Consultants Pvt. Ltd. as the Project Management Consultant.",
    "Tender notice dated 15th March, 2025 was published. 5 developers submitted offers which were evaluated by the PMC.",
    f"At the SGBM held on 20th July, 2025 in the presence of the authorised officer, 21 members present, the members resolved to select and appoint {DEV} as the developer.",
])
docx("Order_79A_Deputy_Registrar.docx", [
    "OFFICE OF THE DEPUTY REGISTRAR, CO-OPERATIVE SOCIETIES (CIDCO), NAVI MUMBAI",
    f"Subject: Redevelopment of {SOC} under Section 79A.",
    "Order dated 05th August, 2025: The selection of the developer at the SGBM held on 20th July, 2025 is recorded in accordance with the directions under Section 79A.",
])
docx("Developer_Final_Offer.docx", [
    DEV,
    "Date: 01/07/2025",
    f"To, The Secretary, {SOC}",
    "Subject: Final offer for redevelopment.",
    "1. We offer 35% additional RERA carpet area over the existing carpet area to every member, free of cost.",
    "2. Monthly rent of Rs. 28,000/- per month per flat from the date of vacation till possession, with escalation of 10% every 12 months.",
    "3. One-time brokerage of Rs. 28,000/- per flat. Refundable security deposit of Rs. 1,00,000/- per flat.",
    "4. Shifting charges of Rs. 25,000/- per flat and re-shifting charges of Rs. 25,000/- per flat.",
    "5. Corpus fund of Rs. 3,00,000/- per flat payable to the Society.",
    "6. Bank guarantee of Rs. 3,00,00,000/- (Rupees Three Crores) before vacation.",
    "7. Liquidated damages of Rs. 2,00,000/- per month of delay beyond the grace period.",
    "8. We shall obtain approvals within 12 months and complete construction within 36 (thirty-six) months with a grace period of 6 months.",
    "9. 1 car parking per flat.",
    "CIN: U45200MH2010PTC123456   PAN: AAKCS1234F   GSTIN: 27AAKCS1234F1Z5",
])
docx("Developer_Board_Resolution.docx", [
    f"CERTIFIED TRUE COPY OF THE RESOLUTION OF THE BOARD OF DIRECTORS OF {DEV.upper()}",
    "Passed at the meeting of the Board of Directors held on 25th August, 2025.",
    "RESOLVED THAT Shri Rohan Mehta and Shri Ajay Mehta, Directors, be and are hereby authorised to execute the Development Agreement.",
    "CIN: U45200MH2010PTC123456",
])
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Members"
ws.append(["Sr. No.", "Flat No.", "Wing", "Floor", "Name of Member", "Existing Carpet Area (sq. m.)", "New RERA Carpet Area (sq. ft.)", "Bank / Mortgage", "Status / Remarks", "Share Certificate No."])
names = ["Prakash Ramdas Kulkarni", "Meera Anil Joshi", "Vinod Shankar Patil", "Late Shantaram Gopal More", "Sunita Ravi Nair & Ravi K. Nair", "Imran Yusuf Shaikh",
         "Kavita Deepak Rane", "Deepak Mohan Rane", "Ganesh Vitthal Pawar", "Rekha Suresh Iyer", "Arun Kumar Singh", "Farida Abbas Merchant", "Nilesh Dattatray Sawant",
         "Pooja Mahesh Kadam", "Mahesh Raghunath Kadam", "Sanjay Bhimrao Gaikwad", "Anita Joseph D'Souza", "Rahul Prakash Deshmukh", "Snehal Ajit Bhosale",
         "Ganesh Vitthal Pawar", "Lata Narayan Chavan", "Yogesh Manohar Thakur", "Priya Sunil Menon", "Suresh Baburao Jadhav"]
for i, n in enumerate(names):
    floor = ["Ground", "First", "Second", "Third"][i // 6]
    area = 37.16 if i % 2 == 0 else 46.45
    new = round(area * 10.764 * 1.35)
    bank = "State Bank of India" if i in (2, 9, 15) else ""
    remark = "Deceased – transmission pending" if "Late" in n else ""
    ws.append([i + 1, f"A-{i // 6}{i % 6 + 1:02d}", "A", floor, n, area, new, bank, remark, f"SC-{i + 1:03d}"])
wb.save(OUT / "Member_Register.xlsx")
print("Simulated project written to", OUT.resolve())
