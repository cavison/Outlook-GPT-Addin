# -*- coding: utf-8 -*-
"""Rebuild the Service Grid (MIM) tab: N/A on all five functions, the owner
decisions from the 18 Sep worksheet session, and a staffing & expense column."""
import openpyxl, os
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L

FONTNAME='Arial'
def font(b=False,sz=10,color='000000',i=False): return Font(name=FONTNAME,bold=b,size=sz,color=color,italic=i)
HDR=PatternFill('solid',fgColor='1F3864')
GOOD=PatternFill('solid',fgColor='E2EFDA'); BET=PatternFill('solid',fgColor='DDEBF7'); BEST=PatternFill('solid',fgColor='FCE4D6')
GRP1=PatternFill('solid',fgColor='FFFFFF'); GRP2=PatternFill('solid',fgColor='F4F6F8')
WRAP=Alignment(wrap_text=True,vertical='top'); CEN=Alignment(horizontal='center',vertical='center',wrap_text=True)
THIN=Side(style='thin',color='BFBFBF'); BOX=Border(left=THIN,right=THIN,top=THIN,bottom=THIN)
SG_OK=PatternFill('solid',fgColor='C6EFCE'); SG_OPEN=PatternFill('solid',fgColor='FFEB9C')
SG_UNC=PatternFill('solid',fgColor='F8CBAD'); SG_REP=PatternFill('solid',fgColor='EDEDED')
SG_NA=PatternFill('solid',fgColor='D0CECE'); SG_MIM=PatternFill('solid',fgColor='C6EFCE')
SG_STF=PatternFill('solid',fgColor='FFF2CC')
LV_NA=PatternFill('solid',fgColor='808080'); LV_G=PatternFill('solid',fgColor='548235')
LV_B=PatternFill('solid',fgColor='2E75B6'); LV_X=PatternFill('solid',fgColor='C55A11')

OWN='Curtis Avison, Life Enrichment (function owner). Structure and terms set 18 Sep 2026 in the tier worksheet session.'
JUS_M=('Owner: Justin Hollabaugh, Settings — assigned 18 Sep 2026. Maintenance was NOT discussed as a separate '
       'service line on the recorded portion of the 17 Sep call, so the terms below have not yet been put to him.')

# Function | Level | Offering | Delivered | MIM | Confirmed by | Status | Staffing & expense impact
GRID=[
('Transportation','N/A',
 'No shuttle and no involvement in transportation. Residents arrange their own rides. This is published as a term of the offering, not left silent.',
 'Not offered','Yes',OWN,'Confirmed by owner',
 'None. No vehicle, no driver hours, no contracted spend.'),
('Transportation','GOOD',
 'Cottage residents are invited onto the existing main-building outings and store trips on a space-available basis. Sign-up is first come, first served, but main-building residents hold priority and cottage residents take the seats that remain. There is no cap on how many seats a cottage resident may take and no guaranteed minimum. Personal appointments are not provided at this tier; the team helps coordinate a rideshare or county senior transit.',
 'Included — space-available seating. Coordination only on personal appointments.','Yes',
 OWN+' Seat floor ruled out deliberately: no limit, but cottage residents never hold priority over main-building residents.',
 'Confirmed by owner',
 'No added hours. Existing runs, existing driver, existing vehicle. Sales language must read "space available" and must never read "included transportation".'),
('Transportation','BETTER',
 'Cottage residents sign up for outings on equal footing with main-building residents — one shared first-come pool, with no priority either way. Personal appointments become available to purchase: a flat base fare covering the round trip and the first hour of wait time, with additional wait purchasable in 30-minute blocks. Trips run inside the community’s existing defined service radius.',
 'Included (outings), purchased (personal appointments). Flat base fare plus 30-minute wait increments.','Yes',
 OWN+' Radius = each community’s existing defined radius, which does not change. Wait time = 1 hour included, additional time in 30-minute blocks. Pricing shape = flat base; the fare itself is TBD.',
 'Confirmed by owner',
 'Equal priority on a fixed-capacity vehicle resolves to either more runs or more denials — it is not free. Needs added run hours. Requires per-transaction resident billing. OPEN: the fare.'),
('Transportation','BEST',
 'A dedicated cottage shuttle programme. Outings are designed for cottage residents first, and main-building residents may fill unused seats. Personal appointment transportation is included at no additional cost to the resident, within the community’s defined radius and with the first hour of wait time included; additional wait is purchasable in 30-minute blocks. Where the shuttle or a driver is unavailable, the community may fulfil the trip through a contracted transportation partner.',
 'All-inclusive within the defined radius and the included wait window.','Yes',
 OWN+' Contracted-partner fallback set by the owner: where the shuttle or driver is unavailable, the trip runs through a contracted partner. Airport runs removed from the vocabulary entirely.',
 'Confirmed by owner',
 'Dedicated driver hours, plus a contracted-partner fallback that is a variable expense the community absorbs — resident demand drives it, not our capacity. OPEN: whether outsourced trips are capped per resident per month. Consider pairing with the Life Enrichment Best Cottage Lead rather than staffing two people.'),

('Life Enrichment','N/A',
 'No campus to access — a standalone cottage cluster with no main building. This is not a case of a campus existing and access being withheld. There is no ongoing Life Enrichment programming and no team presence.',
 'Not offered','Yes',OWN,'Confirmed by owner',
 'None. OPEN: MIM reads Yes at every tier, so a new cottage resident is still met by someone. Where Life Enrichment is absent, name who runs the move-in meeting.'),
('Life Enrichment','GOOD',
 'Cottage residents have full access to the community calendar, the fitness centre where one exists, and campus amenities on the same basis as apartment residents, and they are included in the bi-annual community events. Outings are the exception: seats are first come, first served with main-building residents holding priority and cottage residents taking the seats that remain — the same space-available rule as Transportation Good. The programming already exists; this tier invites cottage residents into it as the second priority.',
 'Included','Yes',OWN,'Confirmed by owner',
 'No added programming hours, but participation is not free. More attendees means more event food that Life Enrichment already funds, more bingo prizes and more craft supplies. Budget a variable food and supply increase in proportion to cottage participation — a supply line, not a labour line.'),
('Life Enrichment','BETTER',
 'Cottage residents move from second priority to equal standing — one shared sign-up pool for outings and main-building programming, with no priority either way. On top of that sits a light cottage-specific layer that the residents largely run themselves: a monthly cottage event planning meeting, one monthly cottage happy hour hosted by a Life Enrichment team member, and resident-coordinated activities that staff do not run. Life Enrichment builds and publishes a dedicated cottage calendar out of that planning meeting, capturing what cottage residents already do — a standing bridge club, for example — so a new resident can find their way in immediately rather than discovering it by accident. The bi-annual community events from Good continue.',
 'Included, plus priced classes and outings','Yes',OWN,'Confirmed by owner',
 'No dedicated liaison. A Life Enrichment team member attends the monthly happy hour, which carries its own refreshment cost, plus basic supplies. Cottage-assigned time totals roughly 4 hours a week, 16 hours a month. NOTE: 4 hrs/wk is 17.3 hrs/month — reconcile the weekly and monthly figures before this feeds a pro forma.'),
('Life Enrichment','BEST',
 'A full cottage life enrichment programme of 20 to 40 hours a week, delivered by a dedicated Cottage Lead. Programming and outings are built for cottage residents first and run separately from the main building. A property may choose to invite main-building residents into cottage programming, but it is optional and never required. This is the inversion of Good: the cottage resident is the priority and the programme is designed around them.',
 'Included in the fee','Yes',
 OWN+' The 20–40 hour role is the liaison, titled Cottage Lead. The enrichment credit was removed by the owner.',
 'Confirmed by owner',
 'A dedicated Cottage Lead at 20–40 hrs/wk — 0.5 to 1.0 FTE. OPEN: what sets 20 versus 40; cottage count is the obvious driver and it needs a threshold, because a 2x range cannot be priced. Consider whether this role also covers the Transportation Best cottage shuttle; if so, 20–40 hours has to carry both.'),

('Culinary','N/A',
 'No meal offering at communities where the dining room cannot seat cottage residents.',
 'Not offered','Yes',
 'Kevin 16:01 "you might have to add another category for culinary, which is worst, which means I can’t do it." Kevin 11:42 "In a community type where they don’t have a large enough dining room, honestly, I don’t want to offer anything." Kevin 2:46 gives the case: "if you had a standalone MC and you had villas around it. You have no ability to feed them in the main building."',
 'Confirmed on call',
 'None. This is the category Kevin asked for by name.'),
('Culinary','GOOD',
 'Dining venues open to cottage residents at posted prices, eaten in the main building. Weekly coffee social or continental breakfast at the clubhouse. Guest meals à la carte. Resident pickup permitted. No delivery.',
 'Purchased — not in the fee','Yes',
 'Kevin 0:03 "a general rule for me would be you can purchase meals as a meal package or meals a la carte, but you have to come to the main building to eat them." Kevin 12:08 on pickup: "Pick up is better."',
 'Confirmed on call',
 'No added kitchen hours at low volume. Requires per-transaction resident billing. A pickup window has to be defined or it lands in the middle of main-building service.'),
('Culinary','BETTER',
 'Adds a purchased meal package or à la carte meals, eaten in the main building, plus resident pickup. Available only where the dining room has capacity.',
 'Purchased — not in the fee','Yes',
 'Kevin 11:21 "I want to offer a la carte meals or meal packages that a resident can... buy where they come into the main building and eat a meal where that is possible, in community types where that is possible."',
 'Confirmed on call',
 'Covers bought by package are forecastable, which is what makes this staffable. Census funds food through per-resident-day; labour is not calculated that way, so the hours have to be requested up front (Kevin 2:13).'),
('Culinary','BEST',
 'A limited included meal allowance, staggered to protect the dining room, rising to an included daily meal only where genuine surplus dining capacity exists and the unit is priced at full IL rate.',
 'Included — capacity-gated','Yes',
 'Kevin 4:12 is the ceiling he offered: "I wouldn’t give it away... I guess you could include one meal a week or something like that... not every day of the week, and then hope for them to stagger that enough." Curtis 3:50 described the top case: "the best where it’s like Plymouth and it’s included like an IL apartment at full rate."',
 'Partly agreed — Kevin resisted daily inclusion',
 'Any included meal is a standing cover commitment at a fixed seat count, so this tier is gated by the dining room before it is gated by price. OPEN: the allowance unit.'),

('Settings: Housekeeping','N/A',
 'No housekeeping offering at communities that cannot staff it.',
 'Not offered','Yes',
 'Justin 15:17 "we’d have to go community by community, because I can’t universally say that." Curtis 15:30 gave the case: "an Arbor Grove with four apartments or whatever... if we can, we’ll help, but otherwise we’re not going to do it."',
 'Confirmed on call','None.'),
('Settings: Housekeeping','GOOD',
 'À la carte only, at a published rate on a unit we define. Move-in and move-out turnover clean.',
 'Purchased — not in the fee','Yes',
 'Justin 7:47 "moving forward, we would change it to... hey, it’s a la carte. Do you want the package, right?" Justin 14:26 "we a la carte includes the packages." Justin 8:55 on who sets the unit: "Yes, yeah, we would define it right."',
 'Confirmed on call',
 'OPEN on the pricing unit. A cottage clean runs two to four hours at Flourish today (Justin 6:27). Requires per-transaction resident billing.'),
('Settings: Housekeeping','BETTER',
 'A defined package available for purchase, plus à la carte add-ons and scheduling. The package contents are not yet defined.',
 'Purchased. OPEN: the report and the market put bi-weekly INSIDE the fee; Justin framed it as purchased.','Yes',
 'Justin 9:13 "if we were to put a package in place, it would say, we’re going to do these 10 things as part of the package." Justin 14:58 conditions: "they have the right equipment, the right people... we determine what that’s actually going to be and it’s not a loss in revenue."',
 'OPEN — decision needed',
 'Justin’s four conditions apply and must be met community by community: the right equipment, the right people, a scope we define, and not a loss in revenue.'),
('Settings: Housekeeping','BEST',
 'Weekly housekeeping with flat-linen service included, plus an annual deep clean.',
 'Included in the fee','Yes',
 'NOT agreed by Justin. He never agreed to put housekeeping in the fee. Live counter-example: Flourish runs this today and Justin 7:13 said "Yeah, we are right now, but it’s got to change", because a proper clean takes "two to three, maybe 4 hours" (6:27).',
 'NOT CONFIRMED — contradicted by Flourish',
 'This is the market standard — Five Star runs weekly with flat linen at 5 of 5 — and it is also the model Flourish is pulling back. Two to four hours per clean is the figure that decides it.'),

('Settings: Maintenance','N/A',
 'No cottage-specific maintenance programme beyond the landlord and lease obligation on the building itself. We own the building, so this never means the structure goes unmaintained.',
 'Not offered','Yes',JUS_M,'Owner assigned — terms not confirmed',
 'None beyond the existing building obligation.'),
('Settings: Maintenance','GOOD',
 'All exterior maintenance, lawn, landscaping, snow and ice, plus repair of community-owned appliances and systems. Business-hours work orders with an emergency line.',
 'Included in the base fee','Yes',JUS_M,'Owner assigned — terms not confirmed',
 'Existing maintenance staff, but a cottage neighbourhood adds travel time per work order that an apartment corridor does not. Both leaders raised spread-out sites independently.'),
('Settings: Maintenance','BETTER',
 'Adds 24-hour emergency maintenance and preventive interior work (filters, detectors, seasonal checks). Resident-requested handyman jobs at a posted rate.',
 'Included, plus a posted handyman rate','Yes',JUS_M,'Owner assigned — terms not confirmed',
 '24-hour coverage is an on-call rota, not a task. Requires per-transaction resident billing for the handyman line.'),
('Settings: Maintenance','BEST',
 'Adds included handyman hours each month, seasonal exterior services (gutters, power-washing, windows) and a scheduled interior refresh cycle.',
 'All-inclusive fee','Yes',JUS_M,'Owner assigned — terms not confirmed',
 'Included hours are the cap — without a monthly hour figure this is an unbounded labour promise. Seasonal services are predictable and schedulable, which makes them the cheapest part of the tier.'),
]

STFILL={'Confirmed on call':SG_OK,'Confirmed by owner':SG_OK,
        'Partly agreed — Kevin resisted daily inclusion':SG_OPEN,'OPEN — decision needed':SG_OPEN,
        'NOT CONFIRMED — contradicted by Flourish':SG_UNC,'Owner assigned — terms not confirmed':SG_UNC}
LVFILL={'N/A':LV_NA,'GOOD':LV_G,'BETTER':LV_B,'BEST':LV_X}
LVBODY={'N/A':PatternFill('solid',fgColor='E7E6E6'),'GOOD':GOOD,'BETTER':BET,'BEST':BEST}

def title(ws,r,text,sz=14):
    c=ws.cell(r,1,text); c.font=font(True,sz,'1F3864')

def build_grid(wb):
    if 'Service Grid (MIM)' in wb.sheetnames:
        idx=wb.sheetnames.index('Service Grid (MIM)')
        del wb['Service Grid (MIM)']
        sg=wb.create_sheet('Service Grid (MIM)',idx)
    else:
        sg=wb.create_sheet('Service Grid (MIM)')

    title(sg,1,'Service Grid — five functions, four levels, with MIM on every option',16)
    sg.cell(2,1,'The working decision grid. Five functions, each with four levels — N/A, Good, Better and Best — and a MIM column that must read Yes on every one of the twenty options. MIM = for every new cottage resident, the team meets them. It reads Yes even at N/A, because the team still meets a new resident to explain what is and is not available at that community. The Confirmed by column carries the owner and, where it exists, the speaker and timestamp from the 17 September call, so any row can be traced back to what was actually said. The final column carries the staffing and expense impact of each level; it is the raw material for deciding which level a given property can actually deliver.').font=font(i=True,sz=10)
    sg.merge_cells('A2:H2'); sg.cell(2,1).alignment=WRAP; sg.row_dimensions[2].height=74
    sg.cell(3,1,'Sources: "Connect - cottage services" meeting transcript, 17 September 2026 — Kevin Penn (Culinary), Justin Hollabaugh (Settings: housekeeping and maintenance), Curtis Avison. Plus the tier worksheet session of 18 September 2026, in which Curtis Avison set Transportation and Life Enrichment as function owner and Maintenance was assigned to Justin Hollabaugh.').font=font(i=True,sz=9)
    sg.merge_cells('A3:H3'); sg.cell(3,1).alignment=WRAP; sg.row_dimensions[3].height=30

    HG=5
    hdg=['Function','Level','Service offering at this level','How it is delivered','MIM',
         'Confirmed by (owner, or speaker and timestamp)','Status','Staffing & expense impact']
    fg=[HDR,HDR,HDR,HDR,PatternFill('solid',fgColor='548235'),HDR,HDR,PatternFill('solid',fgColor='7F6000')]
    for j,(v,fl) in enumerate(zip(hdg,fg),start=1):
        c=sg.cell(HG,j,v); c.font=font(True,10,'FFFFFF'); c.fill=fl; c.alignment=CEN; c.border=BOX
    sg.row_dimensions[HG].height=44

    r=HG+1; prev=None; gidx=-1; starts={}
    for row in GRID:
        fn=row[0]
        if fn!=prev: gidx+=1; prev=fn; starts[fn]=r
        band = GRP1 if gidx%2==0 else GRP2
        for c,v in enumerate(row,start=1):
            cell=sg.cell(r,c,v); cell.alignment=WRAP; cell.border=BOX; cell.font=font(sz=9)
            if c==1: cell.fill=band; cell.font=font(True,11,'1F3864')
            elif c==2: cell.fill=LVFILL[row[1]]; cell.font=font(True,10,'FFFFFF'); cell.alignment=CEN
            elif c in (3,4): cell.fill=LVBODY[row[1]]
            elif c==5: cell.fill=SG_MIM; cell.font=font(True,11,'375623'); cell.alignment=CEN
            elif c==6: cell.fill=band
            elif c==7: cell.fill=STFILL.get(row[6],SG_REP); cell.font=font(True,9); cell.alignment=CEN
            elif c==8: cell.fill=SG_STF
        sg.row_dimensions[r].height=108
        r+=1
    END_G=r-1
    for fn,st in starts.items():
        n=sum(1 for x in GRID if x[0]==fn)
        if n>1:
            sg.merge_cells(start_row=st,start_column=1,end_row=st+n-1,end_column=1)
            sg.cell(st,1).alignment=Alignment(wrap_text=True,vertical='center',horizontal='center')

    r+=1
    sg.cell(r,1,'MIM audit').font=font(True,11,'1F3864')
    sg.cell(r,2,f'=COUNTIF(E{HG+1}:E{END_G},"Yes")&" of "&COUNTA(E{HG+1}:E{END_G})&" options carry MIM = Yes"').font=font(True,11,'375623')
    sg.cell(r,2).fill=SG_MIM; sg.cell(r,2).border=BOX; sg.cell(r,2).alignment=CEN
    sg.merge_cells(start_row=r,start_column=2,end_row=r,end_column=4)
    sg.cell(r,5,f'=IF(COUNTIF(E{HG+1}:E{END_G},"Yes")=COUNTA(E{HG+1}:E{END_G}),"PASS","FAIL")').font=font(True,11)
    sg.cell(r,5).fill=SG_MIM; sg.cell(r,5).border=BOX; sg.cell(r,5).alignment=CEN
    sg.cell(r,6,'Live formula. If any option is ever set to something other than Yes, this reads FAIL.').font=font(i=True,sz=9)
    sg.cell(r,6).alignment=WRAP; sg.merge_cells(start_row=r,start_column=6,end_row=r,end_column=8)
    sg.row_dimensions[r].height=30
    r+=2

    sg.cell(r,1,'Status key:').font=font(True)
    for j,(lbl,fl) in enumerate([('Confirmed by owner / on call',SG_OK),('Open or partly agreed',SG_OPEN),
                                 ('Owner assigned, terms not confirmed',SG_UNC)],start=2):
        c=sg.cell(r,j,lbl); c.fill=fl; c.font=font(sz=9); c.border=BOX; c.alignment=CEN
    sg.row_dimensions[r].height=28
    r+=2

    title(sg,r,'The priority ladder — the spine of Transportation and Life Enrichment',12); r+=1
    LAD=[('N/A','No programme and no involvement.'),
         ('GOOD','Main building holds priority. The service already exists; cottage residents are invited into it on a space-available basis, as the second priority.'),
         ('BETTER','Equal consideration. One shared sign-up pool, no priority either way, plus a light cottage-specific layer the residents largely run themselves.'),
         ('BEST','Cottage residents hold priority. Programming and outings are built for them and run separately; the property may invite main-building residents in, but is never required to.')]
    for lvl,txt in LAD:
        c1=sg.cell(r,1,lvl); c1.fill=LVFILL[lvl]; c1.font=font(True,10,'FFFFFF'); c1.alignment=CEN; c1.border=BOX
        c2=sg.cell(r,2,txt); c2.font=font(sz=9); c2.alignment=WRAP; c2.border=BOX
        sg.merge_cells(start_row=r,start_column=2,end_row=r,end_column=8)
        sg.row_dimensions[r].height=32; r+=1
    r+=1

    title(sg,r,'Five decisions still open',12); r+=1
    DEC=[('1. Housekeeping at Better and Best: in the fee, or purchased?',
          'The report and the market put bi-weekly housekeeping inside the fee — of the communities that mention housekeeping, 87% include it. Justin framed it as purchased at 14:26. This is the single biggest open item and it decides two rows above.'),
         ('2. What separates a property into N/A, Good, Better or Best?',
          'The staffing and expense column is the raw material: a property qualifies for a level when it has those hours and assets. Two fields are needed per property per function — the capability ceiling, set by the function owner, and the selected level, which may sit below it. Note that no operator in the 215-community study varies its service model by community.'),
         ('3. Transportation Best: is the contracted-partner fallback capped?',
          'Best includes personal appointment rides at no cost to the resident and permits outsourcing when no driver is available, so the community absorbs the contractor invoice. That spend is driven by resident demand rather than by our capacity. Cap the trips per resident per month, or accept it as an open exposure.'),
         ('4. Do we pursue a limited included meal at Culinary Best?',
          'Kevin offered one meal a week, staggered, at 4:12, and resisted daily inclusion. The alternative is to keep Best as dine-in only where surplus capacity genuinely exists.'),
         ('5. Pricing unit for housekeeping, and the fare for transportation.',
          'Justin floated 25 cents per square foot at 8:36, prefaced "we might say". Nothing in the 215-community study prices housekeeping by square foot. The transportation fare is a flat base plus 30-minute wait blocks, with the amount still TBD.')]
    for k,v in DEC:
        c1=sg.cell(r,1,k); c1.font=font(True,10,'1F3864'); c1.fill=SG_OPEN; c1.alignment=WRAP; c1.border=BOX
        c2=sg.cell(r,2,v); c2.font=font(sz=9); c2.alignment=WRAP; c2.border=BOX
        sg.merge_cells(start_row=r,start_column=2,end_row=r,end_column=8)
        sg.row_dimensions[r].height=50; r+=1
    r+=1

    title(sg,r,'Figures on the record that are NOT agreed rates',12); r+=1
    for j,v in enumerate(['Figure','Who said it','Status'],start=1):
        c=sg.cell(r,j,v); c.font=font(True,10,'FFFFFF'); c.fill=HDR; c.alignment=CEN; c.border=BOX
    sg.merge_cells(start_row=r,start_column=3,end_row=r,end_column=8); r+=1
    NUMS=[('25 cents per square foot, minus the garage','Justin, 8:36','Hypothetical. Prefaced "we might say". Not a rate.'),
          ('40 to 50 dollars for one hour a week','Curtis, 15:07','Curtis’s own illustration. Justin agreed to the good/better/best structure, not to the price.'),
          ('At least 30% product degradation in transit','Kevin, 4:56','His stated figure, and the basis of his refusal to deliver.'),
          ('Two to three, maybe four hours to clean a Flourish cottage','Justin, 6:27','His stated figure.'),
          ('One FTE a day / an extra 8 hours a week','Curtis, 1:13 and 14:27','Curtis’s illustration of the staffing ask, not an agreed amount.'),
          ('Cottage Lead at 20 to 40 hours a week','Curtis, 18 Sep','Owner proposal for Life Enrichment Best. The 20 versus 40 threshold is not set, and a 2x range cannot be priced.'),
          ('4 hours a week, or 16 hours a month, for Life Enrichment Better','Curtis, 18 Sep','Owner figure. 4 hrs/wk is 17.3 hrs/month — reconcile the two before this feeds a pro forma.'),
          ('Flat base fare plus 30-minute wait blocks','Curtis, 18 Sep','Structure set by the owner. The fare itself is TBD.')]
    for i,row in enumerate(NUMS):
        for c,v in enumerate(row,start=1):
            cell=sg.cell(r,c,v); cell.alignment=WRAP; cell.border=BOX; cell.font=font(sz=9)
            cell.fill = GRP1 if i%2==0 else GRP2
            if c==1: cell.font=font(True,9)
        sg.merge_cells(start_row=r,start_column=3,end_row=r,end_column=8)
        sg.row_dimensions[r].height=30; r+=1
    r+=1
    sg.cell(r,1,'Scope note: this grid covers only the five functions requested; the full ten-function recommendation remains on the Good-Better-Best tab. Transportation and Life Enrichment are confirmed by their function owner. Culinary and Housekeeping reflect the 17 September call, quoted with timestamps. Maintenance has an assigned owner but its terms have not yet been put to him.').font=font(i=True,sz=9)
    sg.merge_cells(start_row=r,start_column=1,end_row=r,end_column=8); sg.cell(r,1).alignment=WRAP
    sg.row_dimensions[r].height=34

    for c,w in {1:20,2:13,3:58,4:30,5:8,6:52,7:20,8:52}.items():
        sg.column_dimensions[L(c)].width=w
    sg.freeze_panes=f'C{HG+1}'
    sg.auto_filter.ref=f'A{HG}:H{END_G}'
    return END_G-HG

REPO='/home/user/Outlook-GPT-Addin'
wb=openpyxl.load_workbook(os.path.join(REPO,'Cottage_Villa_Service_Benchmark.xlsx'))
n=build_grid(wb)
wb.save(os.path.join(REPO,'Cottage_Villa_Service_Benchmark.xlsx'))
print('benchmark workbook updated —',n,'grid rows; tabs:',wb.sheetnames)

solo=openpyxl.Workbook(); solo.remove(solo.active)
build_grid(solo)
out=os.path.join(REPO,'Service_Grid_MIM_2026-09-18.xlsx')
solo.save(out)
print('standalone written:',out)
