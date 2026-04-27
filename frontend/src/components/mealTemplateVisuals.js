import chickenMealImg from '../assets/misc/chickenmeal.png';
import saladImg from '../assets/misc/salad.png';
import notAvailableImg from '../assets/foods_png/notavailable.png';
import chickenImg from '../assets/foods_png/Chicken .png';
import beefImg from '../assets/foods_png/Ground Beef.png';
import steakImg from '../assets/foods_png/Sirloin Steak (lean).png';
import salmonImg from '../assets/foods_png/Salmon.png';
import tilapiaImg from '../assets/foods_png/Tilapia.png';
import tunaImg from '../assets/foods_png/Tuna, Bluefin.png';
import eggsImg from '../assets/foods_png/Regular Eggs.png';
import riceImg from '../assets/foods_png/White Rice.png';
import quinoaImg from '../assets/foods_png/Quinoa.png';
import oatsImg from '../assets/foods_png/Oats.png';
import avocadoImg from '../assets/foods_png/Avocado.png';

const FOOD_IMAGES = [
  { match: 'chicken', image: chickenImg },
  { match: 'ground beef', image: beefImg },
  { match: 'steak', image: steakImg },
  { match: 'salmon', image: salmonImg },
  { match: 'tilapia', image: tilapiaImg },
  { match: 'tuna', image: tunaImg },
  { match: 'egg', image: eggsImg },
  { match: 'white rice', image: riceImg },
  { match: 'brown rice', image: riceImg },
  { match: 'quinoa', image: quinoaImg },
  { match: 'oats', image: oatsImg },
  { match: 'avocado', image: avocadoImg },
];

export function cleanFoodName(value) {
  return String(value || '')
    .replace(/\sSTANDARD$/i, '')
    .trim();
}

function activeSlots(meal) {
  return ['protein_1', 'protein_2', 'carbs_1', 'carbs_2', 'fats_1', 'fats_2']
    .map((slot) => cleanFoodName(meal?.[slot]))
    .filter((name) => name && name !== '-');
}

export function mealTemplateImage(meal) {
  const names = activeSlots(meal).join(' ').toLowerCase();
  const matched = FOOD_IMAGES.find((row) => names.includes(row.match));
  if (matched) return matched.image;
  if (names.includes('rice') || names.includes('pasta') || names.includes('beans')) return chickenMealImg;
  if (names.includes('avocado') || names.includes('oil')) return saladImg;
  return notAvailableImg;
}

export function foodImageForName(value) {
  const name = cleanFoodName(value).toLowerCase();
  const matched = FOOD_IMAGES.find((row) => name.includes(row.match));
  return matched?.image || notAvailableImg;
}

export function productImageForFood(food, canonicalCategory = '') {
  if (food?.image_url) return food.image_url;
  return foodImageForName(food?.display_name || food?.brand_name || canonicalCategory);
}

export function productImageUrl(food) {
  return food?.image_url || '';
}

export function templateCoverImage(template) {
  const meals = Array.isArray(template?.default_day_meals) ? template.default_day_meals : [];
  const firstProteinMeal = meals.find((meal) => cleanFoodName(meal?.protein_1) !== '-');
  return mealTemplateImage(firstProteinMeal || meals[0] || {});
}

export function mealTemplateTitle(meal, fallback = 'Meal Template') {
  const protein = cleanFoodName(meal?.protein_1);
  const carb = cleanFoodName(meal?.carbs_1);
  if (protein && protein !== '-' && carb && carb !== '-') return `${protein} + ${carb}`;
  if (protein && protein !== '-') return protein;
  if (carb && carb !== '-') return carb;
  return fallback;
}

export function mealTemplateDescription(meal) {
  const parts = [];
  const protein = [cleanFoodName(meal?.protein_1), cleanFoodName(meal?.protein_2)].filter((v) => v && v !== '-');
  const carbs = [cleanFoodName(meal?.carbs_1), cleanFoodName(meal?.carbs_2)].filter((v) => v && v !== '-');
  const fats = [cleanFoodName(meal?.fats_1), cleanFoodName(meal?.fats_2)].filter((v) => v && v !== '-');
  if (protein.length) parts.push(`Protein: ${protein.join(' + ')}`);
  if (carbs.length) parts.push(`Carbs: ${carbs.join(' + ')}`);
  if (fats.length) parts.push(`Fats: ${fats.join(' + ')}`);
  return parts.join(' • ') || 'Balanced meal combination';
}

export function mealTemplateBadges(meal, mealSplit, mealContext) {
  const badges = [];
  if (meal?.protein_2 && meal.protein_2 !== '-') badges.push('High Protein');
  if (meal?.carbs_2 && meal.carbs_2 !== '-') badges.push('Higher Carb');
  if (mealContext === 'Post-Workout Meal' || mealContext === 'Pre-Workout Meal') badges.push(mealContext.replace(' Meal', ''));
  if (Number(mealSplit?.grams?.protein_g || 0) < 50 && meal?.protein_2 === '-') badges.push('Simple');
  if (!badges.length) badges.push('Balanced');
  return badges.slice(0, 3);
}
