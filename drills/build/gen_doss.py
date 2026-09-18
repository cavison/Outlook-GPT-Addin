# -*- coding: utf-8 -*-
"""Generate the DOSS reference array for the drills artifact, derived from
dossiers.json so every count and community list in the artifact matches the
aggregation exactly. Narrative lines are hand-written; numbers are not."""
import json, re, io, os

SP = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(SP, 'dossiers.json')))

ORDER = ['Trilogy Health Services','Five Star Senior Living','American Senior Communities',
         'Arrow Senior Living','Life Care Services','Traditions Management',
         'Life Enriching Communities','Capri Communities']

# hand-written: short name, the one-line position, the paragraph, the say-it line, source ids
META = {
 'Trilogy Health Services': dict(nick='Trilogy', tag='The a la carte end',
   line='Bi-weekly housekeeping in the fee. Almost everything else sold as an option.',
   pb='Trilogy is the most consistent operator in the study and the most deliberately unbundled. '
      'Housekeeping appears at all eight villa communities \u2014 bi-weekly at five, bi-monthly at three \u2014 and the clean itself '
      'is recorded as included, though five of those eight lines name laundry service as available rather than included. '
      'Dining appears at only three and is an option at all three. '
      'Laundry and rehab therapy are always "available". Transportation is not listed at a single one of the eight. '
      'Maintenance is in the fee at seven of eight, including one that leads with 24-hour emergency maintenance.',
   say='Trilogy lists housekeeping at all eight and sells the rest. Bi-weekly at most of them, maintenance in the fee at '
       'seven of eight, laundry and dining only as options, and no transportation anywhere in the portfolio.',
   src=['lopez','trilogy_phr']),
 'Five Star Senior Living': dict(nick='Five Star', tag='The bundled end',
   line='Weekly housekeeping with flat linen, and full maintenance, at every property.',
   pb='Five Star has the most bundled service profile of any operator here. Housekeeping is in the fee at all five '
      'communities and four of the five say weekly, three of those naming flat linen service explicitly. '
      'Maintenance is in the fee at all five, described as maintenance of home, building and grounds, or interior and exterior. '
      'Dining shows up at only two of the five, but where it does it is included rather than sold: three daily meals at one, '
      'one daily meal at another. Transportation and life enrichment are not listed at any of the five.',
   say='Five Star is the bundled end. Weekly housekeeping with flat linen and full maintenance at every property, '
       'meals included where they appear at all, and no transportation listed.',
   src=['lopez','fivestar_phr']),
 'American Senior Communities': dict(nick='ASC', tag='Transportation, and little else',
   line='Transportation at all five Garden Home properties, in one identical corporate sentence.',
   pb='American Senior Communities is the transportation operator. Every one of its five Garden Home properties in the '
      'inventory lists transportation, and its own marketing carries one sentence verbatim across all five, naming three '
      'trip purposes: shopping, restaurants and appointments. That is the only function it covers broadly. '
      'Housekeeping appears at one of five. Maintenance at three. Dining, life enrichment and wellness are not listed at any '
      'of the five. The one concrete operational detail anywhere in the research came from a resident review of Coventry Meadows, '
      'not from marketing: a shuttle bus, no charge, mainly doctor appointments, with social outings described as occasional.',
   say='American Senior Communities promises transportation at every Garden Home property, in one identical sentence, '
       'and it is shopping, restaurants and appointments. They list almost nothing else.',
   src=['lopez','asc_sentence','asc_review']),
 'Arrow Senior Living': dict(nick='Arrow / Vitalia', tag='Amenity-led, service-light',
   line='Campus amenities and maintenance. Nothing else listed across seven communities.',
   pb='Arrow\'s Vitalia portfolio is the thinnest service profile of any multi-site operator in the study, and it is '
      'consistent about it. Across all seven Ohio communities the only things listed are campus amenities, which is where '
      'the wellness centre, library and demonstration kitchen sit, and interior and exterior maintenance at three of the seven. '
      'Transportation, housekeeping and dining are absent at all seven. Arrow sells the building and the amenity set, not services.',
   say='Vitalia is amenity-led. Across seven communities they list campus amenities and maintenance, and nothing else. '
       'No transportation, no housekeeping, no dining anywhere in the portfolio.',
   src=['lopez','arrow_phr']),
 'Life Care Services': dict(nick='Life Care Services', tag='The biggest portfolio, the thinnest description',
   line='Nine communities, 462 villas, and mostly the bare word "Transportation".',
   pb='Life Care Services manages the largest villa footprint in the study, nine communities and 462 units, and publishes '
      'the least about what residents get. Transportation appears at four of the nine as the bare noun with no detail. '
      'Housekeeping appears at three, bi-weekly at all three, twice with linen service alongside. Dining appears at exactly one, '
      'Friendship Village of Dublin, as $540 in monthly meal credits, which is the single most specific dining figure in the whole '
      'inventory. Life enrichment and wellness reach villa residents through main-campus amenities rather than as villa services.',
   say='Life Care Services has the biggest villa footprint and the thinnest published detail. Bi-weekly housekeeping where '
       'they mention it, transportation as a single word, and one community running five hundred and forty dollars a month in meal credits.',
   src=['lopez','lcs_phr']),
 'Traditions Management': dict(nick='Traditions', tag='Two-tier language',
   line='Villa residents get the word. Higher acuity gets the defined service.',
   pb='Traditions is the cleanest example of two-tier language in the market. Transportation appears at four of the seven '
      'villa communities as the bare noun, inside a sentence about utilities and full access to dining, amenities, activities '
      'and transportation. On the same operator\'s assisted living and memory care pages the identical benefit is defined: '
      'scheduled transportation to medical appointments and outings. The villa resident is told the word; the higher-acuity '
      'resident is told what it does. Dining is the other distinctive piece: 30 meals a month at two communities, an actual '
      'countable allotment rather than a plan. Maintenance is in the fee at five of seven.',
   say='Traditions describes transportation only for its higher-acuity tiers. Villa residents get the word on its own. '
       'And two of their communities publish thirty meals a month, which is a countable allotment, not a meal plan.',
   src=['lopez','traditions_twotier','traditions_hunter']),
 'Life Enriching Communities': dict(nick='Life Enriching', tag='The allowance playbook',
   line='Housekeeping bundled at all five, but light. Dining runs on a flexible meal allowance.',
   pb='Life Enriching Communities bundles housekeeping at all five communities and does it lightly: bi-weekly at three, '
      'light monthly at two. Maintenance is interior and exterior at all five, the most uniform maintenance language of any '
      'operator here. Dining is where they are distinctive. Their phrase is flexible meal allowance, used at three of the five, '
      'and they run a yearly allowance for health and wellness services at Twin Lakes. An allowance is a credit, which is a '
      'purchase with a subsidy rather than a giveaway.',
   say='Life Enriching uses a flexible meal allowance rather than a meal count, and a yearly wellness allowance too. '
       'Housekeeping is bundled at all five but it is light, bi-weekly or monthly.',
   src=['lopez','lec_phr']),
 'Capri Communities': dict(nick='Capri', tag='Publishes nothing',
   line='Four Wisconsin communities, 71 villas, and one dining allowance between them.',
   pb='Capri is the control case. Across four Wisconsin communities the inventory records no transportation, no housekeeping, '
      'no maintenance, no life enrichment and no wellness. The single service data point in the entire portfolio is a $100 '
      'dining allowance per month at Grace Commons. That is either a genuinely bare product or an operator that does not publish, '
      'and the inventory cannot tell you which. It is worth saying out loud, because it is the honest floor of the market.',
   say='Capri publishes essentially nothing for its villas: one hundred dollars a month in dining at one community and no other '
       'service recorded across four. Either the product is bare or they do not publish it, and we cannot tell which from outside.',
   src=['lopez']),
}

FUNCS = ['Transportation','Life Enrichment','Culinary','Housekeeping','Wellness','Maintenance']

def verdict(fv, ns):
    """Describe coverage and how the line was classified. Deliberately cautious on
    mixed rows: the extra-cost flag often fires on an add-on named in the same
    line (e.g. "Bi-weekly housekeeping; Laundry services available") rather than
    on the base service itself."""
    n = fv['n']
    if n == 0:
        return 'Not listed at any of the ' + str(ns)
    incl, extra = fv.get('incl', 0), fv.get('extra', 0)
    cov = ('all ' + str(ns)) if n == ns else (str(n) + ' of ' + str(ns))
    if extra == 0:
        return 'At ' + cov + ', recorded as included'
    if incl == 0:
        return 'At ' + cov + ', recorded as available at extra cost'
    return ('At ' + cov + ': ' + str(incl) + ' recorded as included, ' + str(extra) +
            ' flagged available — read the phrase, the flag often applies to an add-on in the same line')

def esc(s):
    return (str(s).replace('\\', '\\\\').replace('"', '\\"'))

out = io.StringIO()
out.write('/* DOSS: per-operator reference dossiers. Counts, community lists and quoted\n')
out.write('   phrases are generated from the aggregation, not typed by hand. */\n')
out.write('var DOSS=[\n')
grand_units = 0
for op in ORDER:
    v = D[op]; m = META[op]
    units = 0
    for s in v['sites']:
        units += int(re.match(r'\s*(\d+)', s['units']).group(1))
    grand_units += units
    out.write('{n:"%s",nick:"%s",tag:"%s",ns:%d,units:%d,\n' % (esc(op), esc(m['nick']), esc(m['tag']), v['n'], units))
    out.write(' line:"%s",\n pb:"%s",\n say:"%s",\n s:[%s],\n' % (
        esc(m['line']), esc(m['pb']), esc(m['say']),
        ','.join('"' + x + '"' for x in m['src'])))
    out.write(' sites:[')
    out.write(','.join('{nm:"%s",loc:"%s",u:"%s"}' % (esc(s['nm']), esc(s['loc']), esc(s['units'])) for s in v['sites']))
    out.write('],\n f:[')
    rows = []
    for fn in FUNCS:
        fv = v['f'][fn]
        ph = ','.join('{t:"%s",c:%d,s:[%s]}' % (esc(t['txt']), t['count'],
              ','.join('"' + esc(x) + '"' for x in t['sites'])) for t in fv.get('top', []))
        rows.append('{k:"%s",n:%d,incl:%d,extra:%d,v:"%s",ph:[%s]}' % (
            fn, fv['n'], fv.get('incl', 0), fv.get('extra', 0), esc(verdict(fv, v['n'])), ph))
    out.write(',\n   '.join(rows))
    out.write(']},\n')
out.write('];\n')
out.write('var DOSS_TOTAL={ops:%d,sites:%d,units:%d};\n' % (
    len(ORDER), sum(D[o]['n'] for o in ORDER), grand_units))

open(os.path.join(SP, 'doss.js'), 'w').write(out.getvalue())
print('wrote doss.js', len(out.getvalue()), 'bytes; totals ops=%d sites=%d units=%d' % (
    len(ORDER), sum(D[o]['n'] for o in ORDER), grand_units))
