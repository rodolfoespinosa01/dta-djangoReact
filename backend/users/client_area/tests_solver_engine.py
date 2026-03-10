from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import patch

from django.test import SimpleTestCase

from users.client_area.services.meal_plan_generation.solver import winner_selection
from users.client_area.services.meal_plan_generation.solver.adapters import (
    _nutrition_per_gram_from_food,
    _slot_component,
    _unit_to_gram_factor,
)
from users.client_area.services.meal_plan_generation.solver.candidate_generation import generate_candidates
from users.client_area.services.meal_plan_generation.solver.types import (
    CandidateGenerationConfig,
    CandidateScore,
    MacroTarget,
    MealSolveCandidate,
    MealSolveInput,
    NutritionPerGram,
    ScoredCandidate,
    SolveComponent,
)


@dataclass
class _FakeFood:
    source_food_id: int
    measurement_unit: str
    protein: float
    carbs: float
    fats: float


class SolverNormalizationTests(SimpleTestCase):
    def test_per_gram_unit_normalization(self):
        factor, warning = _unit_to_gram_factor(unit="g", source_food_id=9999)
        self.assertEqual(factor, 1.0)
        self.assertIsNone(warning)

    def test_ounce_unit_normalization(self):
        food = _FakeFood(source_food_id=2001, measurement_unit="oz", protein=28.349523125, carbs=0.0, fats=0.0)
        nutrition, warning = _nutrition_per_gram_from_food(food)
        self.assertIsNone(warning)
        self.assertAlmostEqual(nutrition.protein_g, 1.0, places=6)
        self.assertEqual(nutrition.carbs_g, 0.0)
        self.assertEqual(nutrition.fats_g, 0.0)

    def test_unit_un_rice_cake_normalization(self):
        food = _FakeFood(source_food_id=51, measurement_unit="un", protein=1.0, carbs=7.0, fats=0.0)
        nutrition, warning = _nutrition_per_gram_from_food(food)
        self.assertIn(warning, {None, "configured_unit_grams_by_food_id", "default_unit_grams_by_food_id"})
        self.assertAlmostEqual(nutrition.protein_g, 1.0 / 9.0, places=6)
        self.assertAlmostEqual(nutrition.carbs_g, 7.0 / 9.0, places=6)
        self.assertEqual(nutrition.fats_g, 0.0)

    def test_invalid_unit_food_disables_component(self):
        bad_food = _FakeFood(source_food_id=9999, measurement_unit="", protein=10.0, carbs=0.0, fats=0.0)
        warnings = []
        with patch(
            "users.client_area.services.meal_plan_generation.solver.adapters._find_food_item",
            return_value=bad_food,
        ):
            component = _slot_component(
                key="protein_1",
                name="Broken Food",
                role="protein",
                split_percent=100,
                role_target_g=30,
                warnings_out=warnings,
            )
        self.assertEqual(component.max_serving, 0.0)
        self.assertEqual(component.nutrition_per_gram.protein_g, 0.0)
        self.assertTrue(any("requires_admin_fix" in row.get("warning", "") for row in warnings))


class SolverMathTests(SimpleTestCase):
    def test_achieved_macro_calculation_uses_overlap(self):
        meal_input = MealSolveInput(
            meal_number=1,
            day_of_week="sunday",
            target=MacroTarget(protein_g=20.0, carbs_g=30.0, fats_g=10.0),
            components=[
                SolveComponent(
                    component_key="a",
                    name="Food A",
                    role="carbs",
                    split_percent=50.0,
                    nutrition_per_gram=NutritionPerGram(protein_g=0.10, carbs_g=0.50, fats_g=0.05),
                    min_serving=100.0,
                    max_serving=100.0,
                    step_size=1.0,
                ),
                SolveComponent(
                    component_key="b",
                    name="Food B",
                    role="fats",
                    split_percent=50.0,
                    nutrition_per_gram=NutritionPerGram(protein_g=0.05, carbs_g=0.10, fats_g=0.20),
                    min_serving=50.0,
                    max_serving=50.0,
                    step_size=1.0,
                ),
            ],
            slot_names={"a": "Food A", "b": "Food B"},
            role_targets={"protein": 20.0, "carbs": 30.0, "fats": 10.0},
            metadata={},
        )
        candidates = generate_candidates(
            meal_input=meal_input,
            generation_config=CandidateGenerationConfig(max_candidates=10, branch_beam_width=2),
            combo_template=None,
        )
        self.assertEqual(len(candidates), 1)
        achieved = candidates[0].achieved
        # Food A(100g): P10 C50 F5, Food B(50g): P2.5 C5 F10
        self.assertAlmostEqual(achieved.protein_g, 12.5, places=6)
        self.assertAlmostEqual(achieved.carbs_g, 55.0, places=6)
        self.assertAlmostEqual(achieved.fats_g, 15.0, places=6)

    def test_deterministic_winner_selection(self):
        candidate_low_idx = MealSolveCandidate(
            candidate_index=1,
            candidate_vector={"a": 1.0},
            achieved=MacroTarget(10, 10, 10),
            slot_totals={"a": 1.0},
            component_details_json={},
        )
        candidate_high_idx = MealSolveCandidate(
            candidate_index=2,
            candidate_vector={"a": 2.0},
            achieved=MacroTarget(10, 10, 10),
            slot_totals={"a": 2.0},
            component_details_json={},
        )
        score = CandidateScore(
            delta_protein_g=1.0,
            delta_carbs_g=1.0,
            delta_fats_g=1.0,
            total_error=3.0,
            legacy_error_code=None,
            engine_error_code="V2:1:1:1",
        )
        ranked = winner_selection.select_winner(
            [
                ScoredCandidate(candidate=candidate_high_idx, score=score),
                ScoredCandidate(candidate=candidate_low_idx, score=score),
            ]
        )
        self.assertEqual(ranked.selected.candidate.candidate_index, 1)
