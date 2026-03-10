from __future__ import annotations

from django.core.management.base import BaseCommand

from core.models import MealComboTemplate
from users.client_area.services.meal_plan_generation.solver import (
    CandidateGenerationConfig,
    ScoringConfig,
    adapt_legacy_combo_selection_to_meal_solve_input,
    solve_meal_min_error,
)


class Command(BaseCommand):
    help = "Run debug solver output for a few legacy combo templates."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=3)
        parser.add_argument("--protein", type=float, default=40.0)
        parser.add_argument("--carbs", type=float, default=50.0)
        parser.add_argument("--fats", type=float, default=15.0)

    def handle(self, *args, **options):
        count = max(1, int(options["count"]))
        target_p = float(options["protein"])
        target_c = float(options["carbs"])
        target_f = float(options["fats"])

        combos = list(MealComboTemplate.objects.order_by("combo_id")[: count * 10])
        if not combos:
            self.stdout.write("No combo templates found.")
            return

        selected = []
        for combo in combos:
            if len(selected) >= count:
                break
            slots = [
                combo.protein_slot_1,
                combo.protein_slot_2,
                combo.carb_slot_1,
                combo.carb_slot_2,
                combo.fat_slot_1,
                combo.fat_slot_2,
            ]
            if any(str(slot or "-").strip() != "-" for slot in slots):
                selected.append(combo)

        self.stdout.write("Legacy Solver Sample Debug")
        self.stdout.write("=" * 28)
        self.stdout.write(f"target_macros: protein={target_p} carbs={target_c} fats={target_f}")

        for idx, combo in enumerate(selected, start=1):
            meal_input = adapt_legacy_combo_selection_to_meal_solve_input(
                day_of_week="sunday",
                meal_number=idx,
                combo_template=combo,
                protein_target_g=target_p,
                carbs_target_g=target_c,
                fats_target_g=target_f,
            )
            outcome = solve_meal_min_error(
                meal_input=meal_input,
                combo_template=combo,
                generation_config=CandidateGenerationConfig(max_candidates=500, branch_beam_width=20),
                scoring_config=ScoringConfig(use_legacy_error_lookup=True),
            )
            selected_payload = outcome.audit_row.get("ranked_candidates", [{}])[0]
            achieved = selected_payload.get("achieved", {})
            deltas = selected_payload.get("score", {})
            self.stdout.write("")
            self.stdout.write(f"Sample #{idx} combo_id={combo.combo_id}")
            self.stdout.write(
                "slots: "
                f"p1={combo.protein_slot_1}, p2={combo.protein_slot_2}, "
                f"c1={combo.carb_slot_1}, c2={combo.carb_slot_2}, "
                f"f1={combo.fat_slot_1}, f2={combo.fat_slot_2}"
            )
            self.stdout.write(f"candidate_count={outcome.audit_row.get('candidate_count')}")
            self.stdout.write(f"winner_grams={selected_payload.get('slot_totals', {})}")
            self.stdout.write(
                "achieved_macros="
                f"P:{round(float(achieved.get('protein_g') or 0), 3)} "
                f"C:{round(float(achieved.get('carbs_g') or 0), 3)} "
                f"F:{round(float(achieved.get('fats_g') or 0), 3)}"
            )
            self.stdout.write(
                "target_macros="
                f"P:{target_p} C:{target_c} F:{target_f}"
            )
            self.stdout.write(
                "deltas="
                f"P:{round(float(deltas.get('delta_protein_g') or 0), 3)} "
                f"C:{round(float(deltas.get('delta_carbs_g') or 0), 3)} "
                f"F:{round(float(deltas.get('delta_fats_g') or 0), 3)}"
            )
            self.stdout.write(
                "error_codes="
                f"legacy={deltas.get('legacy_error_code')} "
                f"engine={deltas.get('engine_error_code')}"
            )

