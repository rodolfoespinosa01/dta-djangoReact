function normalizeFoodKey(value) {
  return String(value || '')
    .replace(/\.(png|jpg|jpeg|webp)$/i, '')
    .trim()
    .toLowerCase()
    .replace(/&/g, ' and ')
    .replace(/[_]+/g, ' ')
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function stripCommonVariants(value) {
  let next = value;
  next = next.replace(/\bstandard\b/g, ' ');
  next = next.replace(/\b(low fat|low-fat|lean|milkfat)\b/g, ' ');
  next = next.replace(/\b\d+\s*\/\s*\d+\b/g, ' ');
  next = next.replace(/\b\d+%\b/g, ' ');
  next = next.replace(/\s+/g, ' ').trim();
  return next;
}

const imageContext = require.context('../assets/foods_png', false, /\.(png|jpg|jpeg|webp)$/i);

const imageMap = (() => {
  const map = new Map();
  imageContext.keys().forEach((key) => {
    const fileName = key.replace('./', '');
    if (fileName === '.DS_Store') return;
    const mod = imageContext(key);
    const url = typeof mod === 'string' ? mod : mod?.default;
    const normalized = normalizeFoodKey(fileName);
    if (!normalized || !url || map.has(normalized)) return;
    map.set(normalized, { url, fileName });
  });
  return map;
})();

const EXACT_ALIASES = {
  'beans standard': 'beans',
  'black beans': 'beans',
  'kidney beans': 'beans',
  'chicken breast': 'chicken',
  'coconut oil': 'cocunut oil',
  'oil standard': 'olive oil',
  eggs: 'regular eggs',
  'cottage cheese low fat 1 milkfat': 'cottage cheese',
  'grape fruit pink and red': 'grapefruit',
  'ground beef standard': 'ground beef',
  'ground turkey standard': 'ground turkey',
  'ham 11 fat': 'ham',
  'merluza hake flesh only': 'merluza hake flesh only',
  'nuts standard': 'walnuts',
  'rasberries': 'strawberry',
  strawberries: 'strawberry',
  'steak standard': 'sirloin steak lean',
  'sweet potato': 'sweet potato',
  'tuna bluefin': 'tuna bluefin',
  'white potato': 'white potatoes',
};

function candidateKeysForFoodName(foodName) {
  const base = normalizeFoodKey(foodName);
  if (!base || base === '-') return [];

  const candidates = new Set([base]);
  candidates.add(stripCommonVariants(base));

  const stripped = stripCommonVariants(base);
  if (EXACT_ALIASES[base]) candidates.add(EXACT_ALIASES[base]);
  if (EXACT_ALIASES[stripped]) candidates.add(EXACT_ALIASES[stripped]);

  if (stripped.startsWith('ground beef')) candidates.add('ground beef');
  if (stripped.startsWith('ground turkey')) candidates.add('ground turkey');
  if (stripped.startsWith('tuna ')) candidates.add('tuna bluefin');

  if (stripped.includes('chickpeas')) candidates.add('chickpeas');
  if (stripped.includes('grape fruit')) candidates.add('grapefruit');
  if (stripped.includes('cottage cheese')) candidates.add('cottage cheese');
  if (stripped.includes('merluza') && stripped.includes('hake')) candidates.add('merluza hake flesh only');
  if (stripped === 'oil') candidates.add('olive oil');

  return [...candidates].filter(Boolean);
}

export function getFoodImageAsset(foodName) {
  for (const key of candidateKeysForFoodName(foodName)) {
    const hit = imageMap.get(normalizeFoodKey(key));
    if (hit) return hit;
  }
  return imageMap.get('notavailable') || null;
}

export function getFoodImageUrl(foodName) {
  return getFoodImageAsset(foodName)?.url || null;
}
