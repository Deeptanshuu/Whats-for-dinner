// Cover art for a recipe: an abstract plate seen from above, drawn from the
// recipe's own ingredient palette. It stands where a photo would.
//
// coverSvg(recipe, aspect) is a pure function: the same recipe always gives the
// same picture (all randomness is seeded from the recipe id). It returns the
// inside of an <svg> as a string, plus its viewBox. No network, no image files.
//
// How the data drives the picture:
//   - the first palette item is the dish itself (the pool) and usually sets the ground colour;
//   - the other items are pieces on it, their area split by weight;
//   - an item's name picks its abstract form (cream is a swirl, paneer is cubes, ...);
//   - title, course and cuisine pick the vessel (plate, bowl, thali, banana leaf, glass, tray).

const H = 400; // drawing height in viewBox units; the width follows the aspect ratio
const CHINA = '#f4eedf';
const CHINA_WELL = '#ebe3d0';

// Used when a card has no palette (for example results cached by an older build).
const NEUTRAL = [
  { name: '', color: '#c4ad7c', weight: 60, form: 'pool' },
  { name: '', color: '#efe8d6', weight: 24, form: 'grain' },
  { name: '', color: '#8d9a6c', weight: 16, form: 'leaf' },
];

// ---------- seeded random ----------

function mulberry(seed) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashString(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i += 1) h = Math.imul(h ^ str.charCodeAt(i), 16777619);
  return h >>> 0;
}

// ---------- colour, in OKLCH so tints and shades keep their hue ----------

const toLinear = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const toGamma = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055);
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

export function toLch(hex) {
  const h = /^#?[0-9a-f]{6}$/i.test(hex || '') ? hex.replace('#', '') : 'cdc6b8';
  const r = toLinear(parseInt(h.slice(0, 2), 16) / 255);
  const g = toLinear(parseInt(h.slice(2, 4), 16) / 255);
  const b = toLinear(parseInt(h.slice(4, 6), 16) / 255);
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  const L = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s;
  const A = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s;
  const B = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s;
  return { l: L, c: Math.hypot(A, B), h: Math.atan2(B, A) };
}

// Back to hex. Chroma is reduced until the colour fits in sRGB.
export function fromLch(L, C, h) {
  let c = C;
  for (let k = 0; k < 24; k += 1) {
    const A = c * Math.cos(h);
    const B = c * Math.sin(h);
    const l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3;
    const m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3;
    const s = (L - 0.0894841775 * A - 1.291485548 * B) ** 3;
    const rgb = [
      4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
      -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
      -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
    ];
    if (k === 23 || rgb.every((v) => v >= -0.002 && v <= 1.002)) {
      return `#${rgb.map((v) => Math.round(255 * toGamma(clamp(v, 0, 1))).toString(16).padStart(2, '0')).join('')}`;
    }
    c *= 0.9;
  }
  return '#cdc6b8';
}

// Lighter or darker by `dl`, chroma scaled by `cm`.
function tone(hex, dl, cm = 1) {
  const o = toLch(hex);
  return fromLch(clamp(o.l + dl, 0.12, 0.98), o.c * cm, o.h);
}

// Keep a mark readable on its background: if the two are too close, move its lightness away.
function apart(hex, bg, by = 0.11) {
  const a = toLch(hex);
  const b = toLch(bg);
  const d = Math.hypot(a.l - b.l, a.c * Math.cos(a.h) - b.c * Math.cos(b.h), a.c * Math.sin(a.h) - b.c * Math.sin(b.h));
  if (d > 0.085) return hex;
  return fromLch(clamp(b.l > 0.62 ? b.l - by : b.l + by, 0.15, 0.97), a.c, a.h);
}

const hueGap = (a, b) => {
  const d = Math.abs(a - b);
  return Math.min(d, 2 * Math.PI - d);
};

// ---------- path helpers (all return SVG path data) ----------

const F = (n) => Math.round(n * 10) / 10;
const P = (p) => `${F(p[0])} ${F(p[1])}`;

function rot(x, y, a, cx, cy) {
  const c = Math.cos(a);
  const s = Math.sin(a);
  return [cx + x * c - y * s, cy + x * s + y * c];
}

// A closed smooth curve through the points.
function smooth(p) {
  const n = p.length;
  let d = `M${P(p[0])}`;
  for (let i = 0; i < n; i += 1) {
    const p0 = p[(i - 1 + n) % n];
    const p1 = p[i];
    const p2 = p[(i + 1) % n];
    const p3 = p[(i + 2) % n];
    d += `C${F(p1[0] + (p2[0] - p0[0]) / 6)} ${F(p1[1] + (p2[1] - p0[1]) / 6)} ${F(p2[0] - (p3[0] - p1[0]) / 6)} ${F(p2[1] - (p3[1] - p1[1]) / 6)} ${P(p2)}`;
  }
  return `${d}Z`;
}

const poly = (pts) => `M${pts.map(P).join('L')}Z`;

function circle(cx, cy, r) {
  return `M${F(cx - r)} ${F(cy)}a${F(r)} ${F(r)} 0 1 0 ${F(2 * r)} 0a${F(r)} ${F(r)} 0 1 0 ${F(-2 * r)} 0Z`;
}

// A slightly uneven round shape: a pool of gravy, a dollop.
function blob(cx, cy, r, wobble, n, R) {
  const pts = [];
  const phase = R() * 6.2832;
  for (let i = 0; i < n; i += 1) {
    const a = phase + (i / n) * 6.2832;
    const rr = r * (1 + (R() * 2 - 1) * wobble);
    pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr]);
  }
  return smooth(pts);
}

function lens(cx, cy, len, wid, a) {
  const t1 = rot(-len / 2, 0, a, cx, cy);
  const t2 = rot(len / 2, 0, a, cx, cy);
  return `M${P(t1)}Q${P(rot(0, -wid, a, cx, cy))} ${P(t2)}Q${P(rot(0, wid, a, cx, cy))} ${P(t1)}Z`;
}

function crescent(cx, cy, len, wid, a) {
  const t1 = rot(-len / 2, 0, a, cx, cy);
  const t2 = rot(len / 2, 0, a, cx, cy);
  return `M${P(t1)}Q${P(rot(0, -wid * 1.9, a, cx, cy))} ${P(t2)}Q${P(rot(0, -wid * 0.5, a, cx, cy))} ${P(t1)}Z`;
}

function halfDisc(cx, cy, r, a) {
  return `M${P(rot(-r, 0, a, cx, cy))}A${F(r)} ${F(r)} 0 0 1 ${P(rot(r, 0, a, cx, cy))}Z`;
}

function cube(cx, cy, s, a, R) {
  const h = s / 2;
  const j = () => 1 + (R() - 0.5) * 0.22;
  return poly([
    rot(-h * j(), -h * j(), a, cx, cy), rot(h * j(), -h * j(), a, cx, cy),
    rot(h * j(), h * j(), a, cx, cy), rot(-h * j(), h * j(), a, cx, cy),
  ]);
}

function roundRect(x, y, w, h, r) {
  return `M${F(x + r)} ${F(y)}h${F(w - 2 * r)}a${r} ${r} 0 0 1 ${r} ${r}v${F(h - 2 * r)}a${r} ${r} 0 0 1 ${-r} ${r}`
    + `h${F(-(w - 2 * r))}a${r} ${r} 0 0 1 ${-r} ${-r}v${F(-(h - 2 * r))}a${r} ${r} 0 0 1 ${r} ${-r}Z`;
}

// ---------- rules: ingredient name -> form, recipe -> vessel ----------

// First match wins, so the order matters: "chilli powder" is a powder, "coconut milk"
// a liquid, "pasta sauce" a liquid, and only then do chilli, coconut and pasta get their own forms.
const FORMS = [
  ['powder', /crumbs|zest/],
  ['round', /tortilla|\broti\b|paratha|papad|pizza base|taco|puri|\bbuns?\b|bagel|cookie|biscuit/],
  ['cube', /bread|loaf|baguette|crust|pastry|\bidli\b|\bbadi\b/],
  ['powder', /powder|flour|masala|\batta\b|maida|besan|sooji|semolina|\brava\b|asafoetida|\bhing\b|turmeric|cumin|jeera|peppercorn|pepper corn|black pepper|white pepper|cayenne|paprika|cardamom|clove|cinnamon|nutmeg|\bmace\b|star anise|mustard seed|sesame|poppy|kalonji|ajwain|carom|fennel|methi seed|fenugreek seed|coriander seed|seasoning|sugar|jaggery|\bsalt\b|amchur|chia|flax|basil seeds|\bbran\b|\bmeal\b|cocoa|coffee|\btea\b|\bpodi\b|panch phoran|herbs|dried oregano|dried thyme|dried basil|kasuri|flakes|sichuan|stone flower/],
  ['liquid', /cream|curd|yogurt|yoghurt|milk|syrup|honey|juice|extract|sauce|water|ghee|\boil\b|vinegar|vinaigrette|stock|puree|paste|pulp|pesto|chutney|mayo|ketchup|spread|\bjam\b|marmalade|compote|coulis|custard|decoction|tahini|batter|salsa|mustard|nutella|gulkand|\bdip\b|peanut butter/],
  ['strand', /saffron|spaghetti|linguine|noodle|vermicelli|semiya|\bsev\b|pasta$|lemon ?grass|chives|shavings|slivered|rosemary|drumstick|asparagus|green beans|gawar|strips|sprouts?/],
  ['chilli', /chill|jalapeno|chipotle|prawn|shrimp|cashew/],
  ['leaf', /leaves|leaf|oregano|basil|coriander|cilantro|spinach|mint|methi|parsley|thyme|\bdill\b|lettuce|\bkale\b|arugula|rocket|chard|amaranth|bok choy|greens|cabbage|celery|\bleek|spring onion|bathua|brahmi|salad/],
  ['berry', /pomegranate|cranberr|blueberr|berries|grapes?|olives?|cherr|\bpeas?\b|corn|chana|chickpea|boondi|sabudana|goji|chocolate chips|pearl onion|small onion|shallot|raisin|dates|prunes/],
  ['grain', /\bdal\b|rice|beans?\b|rajma|\bgram\b|lentil|moong|pistachio|almond|walnut|peanut|pecan|nuts?\b|coconut|seeds?\b|ginger|garlic|parmesan|oats|poha|quinoa|barley|millet|bajra|wheat|ragi|granola|muesli|penne|fusilli|macaroni|pasta|soy|kheema|mince|tamarind|kokum|dry fruits|other ingredients/],
  ['cube', /paneer|potato|chicken|chocolate|cheese|tofu|butter|mutton|lamb|fish|meat|pumpkin|kaddu|\byam\b|khoya|bacon|jackfruit|pineapple|papaya|melon|turnip|cauliflower|broccoli|ice cream|vegetables|poosanikai/],
  ['half', /tomato|lemon|lime|strawberr|mango|onion|orange|apple|mushroom|capsicum|pepper|peach|plum|\bfigs?\b|guava|kiwi|avocado|\bamla\b|fruits?\b/],
  ['round', /carrot|beet|brinjal|eggplant|cucumber|\beggs?\b|banana|radish|mooli|zucchini|okra|bhindi|gourd|karela|tindora/],
];
const FALLBACK_FORMS = ['cube', 'half', 'grain', 'leaf', 'powder'];

export function formOf(name, index = 0) {
  const n = String(name || '').toLowerCase();
  for (const [form, re] of FORMS) if (re.test(n)) return form;
  return FALLBACK_FORMS[index % FALLBACK_FORMS.length];
}

// Vessel rules read the main title only ("Palak Paneer", not the part after "Recipe -"),
// because the rest often names a side dish or how it is served.
const DRINK = /\b(lassi|juice|milkshake|shake|smoothie|chai|tea|coffee|kaapi|sharbat|sherbet|cooler|lemonade|mojito|mocktail|cocktail|punch|thandai|buttermilk|chaas|chaach|panna|panha|jal ?jeera|soda|latte|frappe|drink|kashayam|kadha|cappuccino|sangria|shikanji|hot chocolate|spa water)\b/;
// Words that mean the title is food flavoured with a drink, not the drink itself.
const NOT_DRINK = /cake|cookie|muffin|brownie|bread|loaf|pudding|ice cream|biscuit|kulfi|payasam|kheer|waffle|pancake|sandwich|\bnuts\b|powder|masala$|ka masala|\bbowl\b|popsicle|truffle|fudge|mousse|\btart\b|\bpie\b|\brice\b|dosa|pizza|pulao|curry|chicken|halwa|barfi|ladoo|tea time|rusk|scone|toast/;
const TRAY = /\b(blondies?|brownies?|bars?|fudge|barfi|burfi|squares|lasagna|lasagne|casserole|focaccia|chikki|mysore pak|katli)\b/;
// Wet dishes that need a bowl even where a leaf or a flat plate would otherwise be used.
const WET = /\b(soup|shorba|rasam|saaru|stew|broth|kadhi|sambar|sambhar|dal|dhal|curry|kheer|payasam|payasa|kuzhambu|kozhambu|kootu|gravy|theeyal|tambuli|porridge|kanji|ramen|laksa|korma|kurma|makhani|smoothie bowl)\b/;
const SPOONED = /\b(raita|halwa|khichdi|salad|pudding|custard|ice cream|kulfi|dip|hummus|noodles?|upma|oatmeal|pachadi|chutney|pickle|achar|thogayal|saag|bhurji|chaat|sundal|kesari|ganache|sauce|salsa|shrikhand|rabdi|phirni|basundi|mousse|poha|sabzi|masala|bhaji)\b/;
// Desserts that are picked up, not spooned: they sit on a plate.
const HANDHELD = /cake|cookie|biscuit|ladoo|laddu|laadu|popsicle|muffin|donut|doughnut|\bpie\b|\btart\b|\broll|truffle|peda|jalebi|modak|gujiya|pancake|crepe|waffle|toast|sandwich|bread|loaf|scone/;
const SOUTH = /south indian|kerala|tamil|andhra|karnataka|chettinad|udupi|mangalor|malabar|sri lankan/;
const INDIAN = /indian|punjabi|bengali|maharashtrian|rajasthani|gujarati|goan|hyderabadi|awadhi|mughlai|bihari|kashmiri|sindhi|oriya|assamese|lucknowi|malvani|himachal|uttar|haryana|parsi|konkan/;

const mainTitle = (recipe) => String(recipe.title || recipe.name || '')
  .toLowerCase()
  .split(/\s+recipe\b|\s[-|–(]\s?/)[0]
  .trim();

export function vesselOf(recipe) {
  const title = mainTitle(recipe);
  const cuisine = String(recipe.cuisine || '').toLowerCase();
  const course = String(recipe.course || '').toLowerCase();
  if (TRAY.test(title)) return 'tray';
  if (DRINK.test(title) && !NOT_DRINK.test(title)) return 'glass';
  if (WET.test(title)) return 'bowl';
  if (SOUTH.test(cuisine) && !/dessert/.test(course)) return 'leaf';
  if (/\bdosa|\broti|\bnaan|paratha|pizza|sandwich|burger|\bwrap|\btaco/.test(title)) return 'plate';
  if (SPOONED.test(title)) return 'bowl';
  if (/dessert/.test(course) && !HANDHELD.test(title)) return 'bowl';
  if (/lunch/.test(course) && INDIAN.test(cuisine)) return 'thali';
  return 'plate';
}

function readPalette(recipe) {
  const raw = Array.isArray(recipe.palette) ? recipe.palette.filter((p) => p && /^#?[0-9a-f]{6}$/i.test(p.color || '')) : [];
  const items = (raw.length ? raw : NEUTRAL).slice(0, 6);
  return items.map((p, i) => ({
    name: p.name || '',
    color: p.color,
    weight: Number(p.weight) > 0 ? Number(p.weight) : 1,
    lch: toLch(p.color),
    form: p.form || formOf(p.name, i),
  }));
}

// The colour the whole picture leans on: the dominant ingredient, unless it is
// too pale or too grey to carry a field; then the most colourful of the others.
function fieldSource(pal) {
  const d = pal[0];
  const strong = d.lch.c >= 0.055 && d.lch.l <= 0.86 && !(d.lch.l > 0.7 && d.lch.c < 0.075);
  if (strong) return d;
  const other = pal.slice(1).sort((a, b) => b.lch.c * b.weight - a.lch.c * a.weight)[0];
  return other && other.lch.c > Math.max(0.04, d.lch.c) ? other : d;
}

// ---------- the food: a pool with pieces on it, in coordinates centred on 0,0 ----------

const PAINT_ORDER = { liquid: 0, cube: 1, half: 1, round: 1, berry: 2, grain: 2, strand: 3, chilli: 4, leaf: 5, powder: 6 };

function drawDish(pal, region, R, under) {
  const dom = pal[0];
  let rest = pal.slice(1);
  const pool = dom.color;
  // With almost nothing to place, garnish the pool with a tone of itself so it never looks empty.
  if (rest.length < 2) {
    const own = { ...dom, color: tone(pool, dom.lch.l > 0.6 ? -0.13 : 0.15), weight: 30, form: dom.form === 'pool' ? 'grain' : dom.form };
    rest = [...rest, own];
  }
  const sumW = rest.reduce((a, p) => a + p.weight, 0) || 1;
  const isRound = region.type === 'round';
  const rr = region.r;
  const budget = (isRound ? Math.PI * rr * rr : region.w * region.h) * 0.4;
  const taken = []; // [x, y, radius] of pieces already placed
  const turn = R() * 6.2832;
  let out = '';

  if (isRound) {
    out += `<path fill="${pool}" d="${blob(0, 0, rr, 0.035, 11, R)}"/>`;
    out += `<path fill="${tone(pool, dom.lch.l > 0.6 ? -0.045 : 0.05)}" d="${blob(rr * (R() - 0.5) * 0.3, rr * (R() - 0.5) * 0.3, rr * 0.62, 0.13, 8, R)}"/>`;
  } else {
    out += region.draw(pool, tone(pool, dom.lch.l > 0.6 ? -0.04 : 0.05));
  }

  const inside = (x, y, margin) => (isRound ? Math.hypot(x, y) < rr - margin : region.inside(x, y, margin));

  // A free place for a piece of radius `rad`, near angle `th`. Each ingredient keeps to its
  // own arc of the plate, so the arrangement reads as composed, not scattered.
  const spot = (rad, th, span, loose) => {
    for (let k = 0; k < 70; k += 1) {
      let x;
      let y;
      if (isRound) {
        const a = th + (R() - 0.5) * 2 * span * (1 + k / 30);
        const d = rr * (0.12 + 0.74 * Math.sqrt(R()));
        x = Math.cos(a) * d;
        y = Math.sin(a) * d;
      } else {
        x = (R() - 0.5) * region.w;
        y = (R() - 0.5) * region.h;
      }
      if (!inside(x, y, rad * 0.95)) continue;
      const free = taken.every((q) => Math.hypot(q[0] - x, q[1] - y) >= (q[2] + rad) * (loose ? 0.7 : 0.96));
      if (free) {
        taken.push([x, y, rad]);
        return [x, y];
      }
    }
    return null;
  };

  let liquids = 0;
  rest
    .map((p, i) => ({ ...p, th: turn + i * 2.39996 }))
    .sort((a, b) => PAINT_ORDER[a.form] - PAINT_ORDER[b.form] || b.weight - a.weight)
    .forEach((p) => {
      const share = p.weight / sumW;
      const area = budget * share;
      const col = apart(p.color, pool);
      const span = 0.45 + share * 1.9;
      let d = '';
      let d2 = '';
      let n;
      let s;

      if (p.form === 'liquid') {
        const kind = isRound ? liquids : 2;
        liquids += 1;
        if (kind === 0) {
          // a spiral swirl
          const rm = rr * clamp(0.34 + share * 0.9, 0.36, 0.66);
          const turns = 1.55 + R() * 0.5;
          const a0 = R() * 6.28;
          const ox = rr * (R() - 0.5) * 0.24;
          const oy = rr * (R() - 0.5) * 0.24;
          const pts = [];
          for (let i = 0; i <= 54; i += 1) {
            const t = i / 54;
            const an = a0 + t * turns * 6.2832;
            const ra = rm * (0.1 + 0.9 * t);
            pts.push([ox + Math.cos(an) * ra, oy + Math.sin(an) * ra]);
          }
          out += `<path fill="none" stroke="${col}" stroke-linecap="round" stroke-linejoin="round" stroke-width="${F(rr * (0.05 + share * 0.13))}" d="M${pts.map(P).join('L')}"/>`;
          taken.push([ox, oy, rm * 0.35]);
        } else if (kind === 1) {
          // a drizzled arc near the edge
          const ra = rr * 0.8;
          const sweep = 1.1 + share * 3;
          const p1 = [Math.cos(p.th) * ra, Math.sin(p.th) * ra];
          const p2 = [Math.cos(p.th + sweep) * ra, Math.sin(p.th + sweep) * ra];
          out += `<path fill="none" stroke="${col}" stroke-linecap="round" stroke-width="${F(rr * (0.035 + share * 0.1))}" d="M${P(p1)}A${F(ra)} ${F(ra)} 0 0 1 ${P(p2)}"/>`;
        } else {
          // drops
          n = clamp(Math.round(3 + share * 14), 3, 9);
          for (let i = 0; i < n; i += 1) {
            s = Math.sqrt(area / n / Math.PI) * (0.5 + R() * 0.7) * 0.8;
            const pt = spot(s, p.th, 1.2, true);
            if (pt) d += circle(pt[0], pt[1], s);
          }
          out += `<path fill="${col}" d="${d}"/>`;
        }
        return;
      }

      if (p.form === 'cube') {
        n = clamp(Math.round(p.weight / 3.5), 3, 9);
        s = Math.sqrt(area / n) * 0.95;
        for (let i = 0; i < n; i += 1) {
          const size = s * (0.8 + R() * 0.4);
          const pt = spot(size * 0.62, p.th, span);
          if (pt) d += cube(pt[0], pt[1], size, R() * 3.14, R);
        }
        out += `<path fill="${col}" stroke="${col}" stroke-width="${F(s * 0.2)}" stroke-linejoin="round" d="${d}"/>`;
      } else if (p.form === 'half') {
        n = clamp(Math.round(p.weight / 4.5), 2, 7);
        s = Math.sqrt((2 * area) / n / Math.PI) * 1.05;
        for (let i = 0; i < n; i += 1) {
          const r = s * (0.8 + R() * 0.4);
          const a = R() * 6.28;
          const pt = spot(r * 0.78, p.th, span);
          if (pt) {
            d += halfDisc(pt[0], pt[1], r, a);
            d2 += halfDisc(pt[0], pt[1], r * 0.58, a);
          }
        }
        out += `<path fill="${col}" d="${d}"/><path fill="${tone(col, 0.085, 0.9)}" d="${d2}"/>`;
      } else if (p.form === 'round') {
        n = clamp(Math.round(p.weight / 5), 2, 7);
        s = Math.sqrt(area / n / Math.PI);
        for (let i = 0; i < n; i += 1) {
          const r = s * (0.8 + R() * 0.4);
          const pt = spot(r, p.th, span);
          if (pt) {
            d += circle(pt[0], pt[1], r);
            d2 += circle(pt[0], pt[1], r * 0.52);
          }
        }
        out += `<path fill="${col}" d="${d}"/><path fill="${tone(col, 0.09, 0.9)}" d="${d2}"/>`;
      } else if (p.form === 'berry') {
        n = clamp(Math.round(p.weight * 0.9), 6, 24);
        s = clamp(Math.sqrt(area / n / Math.PI) * 1.1, rr * 0.035, rr * 0.085);
        for (let i = 0; i < n; i += 1) {
          const r = s * (0.8 + R() * 0.4);
          const pt = spot(r, p.th, span + 0.9, true);
          if (pt) d += circle(pt[0], pt[1], r);
        }
        out += `<path fill="${col}" d="${d}"/>`;
      } else if (p.form === 'grain') {
        n = clamp(Math.round(p.weight * 1.5), 9, 44);
        s = clamp(Math.sqrt(area / n) * 1.5, rr * 0.07, rr * 0.16);
        for (let i = 0; i < n; i += 1) {
          const pt = spot(s * 0.42, p.th, span + 1.1, true);
          if (pt) d += lens(pt[0], pt[1], s * (0.8 + R() * 0.4), s * 0.36, R() * 3.14);
        }
        out += `<path fill="${col}" d="${d}"/>`;
      } else if (p.form === 'leaf') {
        n = clamp(Math.round(p.weight / 2.6), 3, 9);
        s = clamp(Math.sqrt(area / n) * 2.1, rr * 0.16, rr * 0.4);
        for (let i = 0; i < n; i += 1) {
          const len = s * (0.75 + R() * 0.5);
          const a = R() * 6.28;
          const pt = spot(len * 0.36, p.th, span + 0.4, true);
          if (pt) {
            d += lens(pt[0], pt[1], len, len * 0.4, a);
            d2 += `M${P(rot(-len * 0.36, 0, a, pt[0], pt[1]))}L${P(rot(len * 0.36, 0, a, pt[0], pt[1]))}`;
          }
        }
        out += `<path fill="${col}" d="${d}"/><path fill="none" stroke="${tone(col, -0.1)}" stroke-width="${F(Math.max(1.2, s * 0.045))}" stroke-linecap="round" d="${d2}"/>`;
      } else if (p.form === 'chilli') {
        n = clamp(Math.round(p.weight / 2.6), 2, 7);
        s = clamp(Math.sqrt(area / n) * 2.3, rr * 0.2, rr * 0.46);
        for (let i = 0; i < n; i += 1) {
          const pt = spot(s * 0.3, p.th, span + 0.5, true);
          if (pt) d += crescent(pt[0], pt[1], s * (0.8 + R() * 0.4), s * 0.16, R() * 6.28);
        }
        out += `<path fill="${col}" d="${d}"/>`;
      } else if (p.form === 'strand') {
        const long = /spaghetti|linguine|pasta|noodle|semiya|vermicelli/.test(p.name.toLowerCase());
        n = long ? clamp(Math.round(p.weight * 0.6), 7, 16) : clamp(Math.round(p.weight * 1.1), 6, 18);
        for (let i = 0; i < n; i += 1) {
          const len = long ? rr * (0.7 + R() * 0.7) : rr * (0.16 + R() * 0.14);
          const a = R() * 6.28;
          const c0 = long ? [rr * (R() - 0.5) * 0.7, rr * (R() - 0.5) * 0.7] : (spot(len * 0.2, p.th, 2.2, true) || [0, 0]);
          const ends = [
            rot(-len / 2, 0, a, c0[0], c0[1]),
            rot((R() - 0.5) * len * 0.5, (R() - 0.5) * len * (long ? 1.3 : 0.7), a, c0[0], c0[1]),
            rot(len / 2, 0, a, c0[0], c0[1]),
          ];
          // keep strands on the dish
          ends.forEach((e) => {
            const lim = isRound ? rr * 0.9 : Math.min(region.w, region.h) * 0.45;
            const far = Math.hypot(e[0], e[1]);
            if (far > lim) {
              e[0] *= lim / far;
              e[1] *= lim / far;
            }
          });
          d += `M${P(ends[0])}Q${P(ends[1])} ${P(ends[2])}`;
        }
        out += `<path fill="none" stroke="${col}" stroke-linecap="round" stroke-width="${F(long ? rr * 0.038 : rr * 0.022)}" d="${d}"/>`;
      } else {
        // powder: a dusting that may fall just outside the pool
        n = clamp(Math.round(p.weight * 5), 22, 80);
        for (let i = 0; i < n; i += 1) {
          const a = p.th + (R() - 0.5) * 3.6;
          const far = rr * (0.1 + 0.93 * Math.sqrt(R()));
          const x = isRound ? Math.cos(a) * far : (R() - 0.5) * region.w * 1.02;
          const y = isRound ? Math.sin(a) * far : (R() - 0.5) * region.h * 1.02;
          const r = rr * (0.012 + R() * 0.02) * (R() < 0.12 ? 1.8 : 1);
          if (inside(x, y, 0)) d += circle(x, y, r);
          else d2 += circle(x, y, r);
        }
        out += `<path fill="${col}" d="${d}"/>`;
        if (d2) out += `<path fill="${apart(p.color, under || pool)}" d="${d2}"/>`;
      }
    });
  return out;
}

// ---------- the whole picture ----------

const group = (x, y, angle, inner) => `<g transform="translate(${F(x)} ${F(y)})${angle ? ` rotate(${F(angle)})` : ''}">${inner}</g>`;

// A small side bowl holding one ingredient.
function sideBowl(x, y, r, item, body, R) {
  const c = apart(item.color, body, 0.14);
  return `<circle cx="${F(x)}" cy="${F(y)}" r="${F(r)}" fill="${body}"/>`
    + `<path fill="${c}" d="${blob(x, y, r * 0.8, 0.03, 9, R)}"/>`
    + `<path fill="${tone(c, toLch(c).l > 0.6 ? -0.05 : 0.06)}" d="${blob(x + r * 0.1, y - r * 0.08, r * 0.42, 0.16, 7, R)}"/>`;
}

export function coverSvg(recipe, aspect = 1.5) {
  const id = Number.isFinite(Number(recipe.id)) ? Number(recipe.id) : hashString(String(recipe.title || recipe.name || ''));
  const R = mulberry(Math.imul(id, 2654435761) >>> 0);
  const W = Math.round(H * aspect);
  const pal = readPalette(recipe);
  // Food is never a cool grey pool: fish and other silver-blue ingredients become pieces
  // on the next ingredient instead.
  // Those pieces are drawn silver, with most of the blue taken out.
  const coolGrey = (p) => {
    const deg = (p.lch.h * 180) / Math.PI;
    return p.lch.c < 0.06 && p.lch.c > 0.012 && (deg > 170 || deg < -100);
  };
  if (pal.length > 1 && coolGrey(pal[0])) pal.splice(1, 0, pal.shift());
  pal.forEach((p) => {
    if (!coolGrey(p)) return;
    p.color = fromLch(Math.min(0.9, p.lch.l + 0.08), p.lch.c * 0.3, p.lch.h);
    p.lch = toLch(p.color);
  });
  const dom = pal[0];
  const vessel = vesselOf(recipe);
  const wide = aspect >= 1.8;

  // Ground: one flat field.
  let source = fieldSource(pal);
  if (vessel === 'glass') {
    // A glass has almost no rim, so the ground must not be the drink's own colour.
    const other = pal.slice(1)
      .filter((p) => hueGap(p.lch.h, dom.lch.h) > 0.6 && p.lch.c > 0.05)
      .sort((a, b) => b.lch.c * b.weight - a.lch.c * a.weight)[0];
    if (other) source = other;
  }
  if (vessel === 'leaf') {
    // The leaf is green, so the ground under it should not be.
    const LEAF_HUE = 2.45;
    if (hueGap(source.lch.h, LEAF_HUE) < 0.8) {
      const other = pal
        .filter((p) => hueGap(p.lch.h, LEAF_HUE) >= 0.8 && p.lch.c > 0.05)
        .sort((a, b) => b.lch.c * b.weight - a.lch.c * a.weight)[0];
      source = other || { lch: toLch('#b58a52') };
    }
  }
  const hueDeg = (source.lch.h * 180) / Math.PI;
  let yellow = hueDeg > 55 && hueDeg < 112; // yellows turn to mud when darkened, so they stay light
  let groundL = clamp(source.lch.l - 0.11, yellow ? 0.68 : 0.33, 0.72);
  // A drink on a ground of its own colour would vanish: go light under a dark drink and the reverse.
  if (vessel === 'glass' && source === dom) {
    groundL = dom.lch.l < 0.6 ? 0.76 : 0.42;
    // A dark yellow is mud, so a pale yellow drink sits on leaf green instead.
    if (yellow && dom.lch.l >= 0.6) source = { lch: { l: 0.45, c: 0.085, h: 2.45 } };
  }
  // A small seeded shift, so a page of similar dishes is not one repeated colour.
  groundL += (R() - 0.5) * 0.07;
  const ground = fromLch(
    groundL,
    clamp(source.lch.c * (yellow && source.lch.h < 2 ? 1.05 : 0.98), 0.045, 0.128), // never a dead grey
    source.lch.h + (R() - 0.5) * 0.14,
  );
  const groundLch = toLch(ground);

  // Crockery: warm porcelain, or dark stoneware when the food itself is pale.
  const palePool = dom.lch.l > 0.85 || (dom.lch.l > 0.76 && dom.lch.c < 0.06);
  const darkest = pal.slice().sort((a, b) => a.lch.l - b.lch.l)[0];
  let china = CHINA;
  let well = CHINA_WELL;
  if (palePool) {
    china = darkest.lch.l < 0.5 ? tone(darkest.color, -0.08, 0.8) : fromLch(0.27, 0.05, groundLch.h);
    china = apart(china, ground, 0.12);
    well = tone(china, 0.05);
  }

  const side = R() < 0.5 ? -1 : 1; // which way the vessel sits off centre
  let cx = W / 2 + side * W * (wide ? 0.13 : 0.09);
  let cy = H / 2 + (R() - 0.5) * 44;

  // Ingredients for the side bowls: the most colourful ones that are not the ground's own.
  const extras = pal.slice(1).filter((p) => p !== source).sort((a, b) => b.lch.c - a.lch.c);
  let body = `<rect width="${W}" height="${H}" fill="${ground}"/>`;
  let radius; // how far the vessel reaches, for placing things beside it
  let sideRadius = 60;
  let beside = true; // draw a side bowl and loose marks in the empty part of the ground

  if (vessel === 'plate') {
    radius = 212;
    body += group(cx, cy, 0, `<circle r="${radius}" fill="${china}"/><circle r="${F(radius * 0.77)}" fill="${well}"/>${drawDish(pal, { type: 'round', r: radius * 0.67 }, R, well)}`);
  } else if (vessel === 'bowl') {
    radius = 184;
    body += group(cx, cy, 0, `<circle r="${radius}" fill="${china}"/><circle r="${F(radius * 0.9)}" fill="${well}"/>${drawDish(pal, { type: 'round', r: radius * 0.83 }, R, well)}`);
  } else if (vessel === 'thali') {
    // A wide plate with the dish to one side and two small bowls on it.
    radius = 236;
    beside = false;
    let inner = `<circle r="${radius}" fill="${china}"/><circle r="${F(radius * 0.9)}" fill="${well}"/>`;
    inner += group(-side * radius * 0.2, radius * 0.1, 0, drawDish(pal, { type: 'round', r: radius * 0.56 }, R, well));
    if (extras[0]) inner += sideBowl(side * radius * 0.47, -radius * 0.44, radius * 0.2, extras[0], china, R);
    if (extras[1]) inner += sideBowl(side * radius * 0.64, radius * 0.06, radius * 0.17, extras[1], china, R);
    body += group(cx - side * W * 0.03, cy, 0, inner);
  } else if (vessel === 'glass') {
    // Two glasses seen from above, the second one cropped by the edge.
    radius = 128;
    cx = W / 2 + side * W * (wide ? 0.2 : 0.13);
    cy = H * 0.46;
    const rim = '#f6f1e4';
    const glass = (rng) => `<circle r="${radius}" fill="${rim}"/><circle r="${F(radius * 0.9)}" fill="${tone(dom.color, -0.06)}"/>${drawDish(pal, { type: 'round', r: radius * 0.86 }, rng, rim)}`;
    body += group(cx - side * radius * 1.72, cy + radius * 1.18, 0, glass(mulberry(id + 7)));
    body += group(cx, cy, 0, glass(R));
    sideRadius = 50;
  } else if (vessel === 'tray') {
    // A baking tray cut into squares, one already taken.
    const tw = 392;
    const th = 292;
    const cols = 3;
    const rows = 2;
    const gap = 7;
    const pad = 16;
    const cw = (tw - pad * 2 - gap * (cols - 1)) / cols;
    const ch = (th - pad * 2 - gap * (rows - 1)) / rows;
    const missing = Math.floor(R() * cols * rows);
    const cells = [];
    for (let j = 0; j < rows; j += 1) {
      for (let i = 0; i < cols; i += 1) {
        if (j * cols + i !== missing) cells.push([-tw / 2 + pad + i * (cw + gap), -th / 2 + pad + j * (ch + gap)]);
      }
    }
    // The tray contrasts with the slab: dark under a light bake, pale under a dark one.
    let trayColor = CHINA;
    if (palePool) trayColor = china;
    else if (dom.lch.l >= 0.6) trayColor = apart(tone(dom.color, -0.36, 0.6), ground, 0.14);
    const region = {
      type: 'rect',
      w: tw - pad * 2,
      h: th - pad * 2,
      r: 118,
      inside: (x, y, m) => cells.some((c) => x > c[0] + m && x < c[0] + cw - m && y > c[1] + m && y < c[1] + ch - m),
      draw: (fill, fill2) => {
        let d = '';
        let d2 = '';
        cells.forEach((c) => { d += roundRect(c[0], c[1], cw, ch, 7); });
        cells.forEach((c, n) => {
          if (n % 2 === 0) d2 += blob(c[0] + cw * (0.3 + R() * 0.4), c[1] + ch * (0.3 + R() * 0.4), cw * 0.26, 0.2, 7, R);
        });
        return `<path fill="${fill}" d="${d}"/><path fill="${fill2}" d="${d2}"/>`;
      },
    };
    body += group(cx, cy, (R() - 0.5) * 14, `<path fill="${trayColor}" d="${roundRect(-tw / 2, -th / 2, tw, th, 20)}"/>${drawDish(pal, region, R, trayColor)}`);
    radius = 205;
  } else {
    // Banana leaf: the dish served straight on it, with a small bowl and a dollop beside.
    const green = pal.find((p) => {
      const deg = (p.lch.h * 180) / Math.PI;
      return deg > 105 && deg < 165 && p.lch.c > 0.05;
    });
    let leaf = green ? fromLch(0.5, 0.1, clamp(green.lch.h, 2.3, 2.6)) : '#4f7d49';
    if (Math.abs(toLch(leaf).l - groundLch.l) < 0.1 && hueGap(toLch(leaf).h, groundLch.h) < 0.6) leaf = tone(leaf, groundLch.l > 0.5 ? -0.1 : 0.12);
    const lw = W * 1.05;
    const lh = 318;
    const pts = [];
    for (let q = 0; q < 22; q += 1) {
      const t = (q / 22) * 6.2832;
      const ex = Math.cos(t);
      const ey = Math.sin(t);
      pts.push([Math.sign(ex) * Math.abs(ex) ** 0.42 * (lw / 2), Math.sign(ey) * Math.abs(ey) ** 0.7 * (lh / 2) * (1 + (R() - 0.5) * 0.04)]);
    }
    let veins = '';
    for (let v = -9; v <= 9; v += 1) {
      const vx = (v * lw) / 20 + 8;
      veins += `M${F(vx)} 0L${F(vx + 26)} ${F(-lh / 2)}M${F(vx)} 0L${F(vx + 26)} ${F(lh / 2)}`;
    }
    const clip = `leaf-${id}-${W}`;
    const outline = smooth(pts);
    body += group(W / 2, H / 2 + 6, -9 * side,
      `<clipPath id="${clip}"><path d="${outline}"/></clipPath><path fill="${leaf}" d="${outline}"/>`
      + `<g clip-path="url(#${clip})"><path fill="none" stroke="${tone(leaf, -0.045)}" stroke-width="2" d="${veins}"/>`
      + `<path stroke="${tone(leaf, 0.1)}" stroke-width="6" stroke-linecap="round" d="M${F(-lw / 2)} 0H${F(lw / 2)}"/></g>`);
    const food = pal.map((p, i) => (i ? p : { ...p, color: apart(p.color, leaf, 0.14) }));
    body += group(cx, cy, 0, drawDish(food, { type: 'round', r: 122 }, R, leaf));
    if (extras[0]) body += sideBowl(cx - side * 205, cy - 62, 44, extras[0], CHINA, R);
    if (extras[1]) body += `<path fill="${apart(extras[1].color, leaf, 0.14)}" d="${blob(cx - side * 190, cy + 64, 34, 0.08, 8, R)}"/>`;
    beside = false;
    radius = 122;
  }

  // The empty part of the ground: one small bowl and a few loose marks.
  const sideItem = extras[0] || pal[1];
  if (beside && sideItem) {
    const top = R() < 0.5;
    let sx = side > 0 ? Math.max(sideRadius * 0.45, cx - radius - sideRadius * 0.9) : Math.min(W - sideRadius * 0.45, cx + radius + sideRadius * 0.9);
    let sy = top ? H * 0.2 : H * 0.8;
    if (vessel === 'glass') {
      sx = clamp(cx + side * radius * 1.5, 20, W - 20);
      sy = Math.min(H + 6, cy + radius * 1.75);
    }
    body += sideBowl(sx, sy, sideRadius, sideItem, CHINA, R);
    if (wide && vessel !== 'glass' && extras[1]) body += sideBowl(side > 0 ? 6 : W - 6, top ? H * 0.74 : H * 0.26, 74, extras[1], CHINA, R);

    const loose = pal.slice(1).find((p) => ['grain', 'leaf', 'chilli', 'powder', 'berry'].includes(p.form));
    if (loose) {
      const col = apart(loose.color, ground, 0.16);
      const n = loose.form === 'powder' ? 16 : 7;
      let d = '';
      for (let z = 0; z < n; z += 1) {
        let lx = sx + (R() - 0.5) * 120;
        let ly = (top ? H * 0.72 : H * 0.28) + (R() - 0.5) * 130;
        if (vessel === 'glass') {
          lx = cx - side * (radius * 0.2 + R() * radius * 1.6);
          ly = 18 + R() * 60;
        }
        if (Math.hypot(lx - cx, ly - cy) < radius + 8) continue;
        if (loose.form === 'powder') d += circle(lx, ly, 2 + R() * 3);
        else if (loose.form === 'berry') d += circle(lx, ly, 5 + R() * 3);
        else if (loose.form === 'chilli') d += crescent(lx, ly, 34, 5.5, R() * 6.28);
        else if (loose.form === 'leaf') d += lens(lx, ly, 30 + R() * 10, 12, R() * 6.28);
        else d += lens(lx, ly, 15 + R() * 6, 5.5, R() * 6.28);
      }
      if (d) body += `<path fill="${col}" d="${d}"/>`;
    }
  }

  return { viewBox: `0 0 ${W} ${H}`, body, vessel };
}

// ---------- the shared paper grain ----------

// One small noise tile, made once on a canvas and reused by every cover as a CSS
// background, so the flat colours read as print, not as screen fills.
let grain = null;
export function grainUrl() {
  if (grain !== null) return grain;
  grain = '';
  try {
    const size = 180;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    const image = ctx.createImageData(size, size);
    const R = mulberry(9001);
    for (let i = 0; i < image.data.length; i += 4) {
      const v = R();
      const shade = v < 0.5 ? 40 : 255;
      image.data[i] = shade;
      image.data[i + 1] = shade;
      image.data[i + 2] = shade;
      image.data[i + 3] = (Math.abs(v - 0.5) * 2) ** 2.2 * 255 * 0.2;
    }
    ctx.putImageData(image, 0, 0);
    grain = `url(${canvas.toDataURL('image/png')})`;
  } catch {
    grain = ''; // no canvas: the covers are simply flat
  }
  return grain;
}
