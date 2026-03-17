from django.core.paginator import Paginator
from django.db.models import Q

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from core.models import ComboMacroErrorLookup, FoodLibraryItem, MealComboTemplate
from .api_contract import error, ok, require_superadmin


def _parse_int(value, default, min_value=1, max_value=100):
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, min_value), max_value)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def food_library_browser(request):
    auth_error = require_superadmin(request)
    if auth_error:
        return auth_error

    mode = (request.query_params.get("mode") or "foods").strip().lower()
    if mode not in {"foods", "combos", "errors"}:
        return error(
            code="INVALID_MODE",
            message="Mode must be one of: foods, combos, errors.",
            http_status=400,
        )

    query = (request.query_params.get("q") or "").strip()
    page = _parse_int(request.query_params.get("page"), 1)
    page_size = _parse_int(request.query_params.get("page_size"), 25, 1, 100)

    counts = {
        "foods": FoodLibraryItem.objects.count(),
        "combos": MealComboTemplate.objects.count(),
        "errors": ComboMacroErrorLookup.objects.count(),
    }

    if mode == "foods":
        qs = FoodLibraryItem.objects.all().order_by("source_food_id")
        macro = (request.query_params.get("macro") or "").strip()
        if macro:
            qs = qs.filter(macro=macro)
        category = (request.query_params.get("category") or "").strip()
        if category:
            qs = qs.filter(category=category)
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(source_food_id__icontains=query))
        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)
        items = [
            {
                "id": row.source_food_id,
                "macro": row.macro,
                "category": row.category,
                "name": row.name,
                "measurement_unit": row.measurement_unit,
                "protein": float(row.protein),
                "carbs": float(row.carbs),
                "fats": float(row.fats),
                "is_placeholder": row.is_placeholder,
            }
            for row in page_obj.object_list
        ]
    elif mode == "combos":
        qs = MealComboTemplate.objects.all().order_by("combo_id")
        if query:
            qs = qs.filter(
                Q(combo_id__icontains=query)
                | Q(protein_slot_1__icontains=query)
                | Q(protein_slot_2__icontains=query)
                | Q(carb_slot_1__icontains=query)
                | Q(carb_slot_2__icontains=query)
                | Q(fat_slot_1__icontains=query)
                | Q(fat_slot_2__icontains=query)
            )
        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)
        items = [
            {
                "id": row.combo_id,
                "protein_slot_1": row.protein_slot_1,
                "protein_slot_2": row.protein_slot_2,
                "carb_slot_1": row.carb_slot_1,
                "carb_slot_2": row.carb_slot_2,
                "fat_slot_1": row.fat_slot_1,
                "fat_slot_2": row.fat_slot_2,
                "protein_split_1": float(row.protein_split_1 or 0),
                "protein_split_2": float(row.protein_split_2 or 0),
                "carb_split_1": float(row.carb_split_1 or 0),
                "carb_split_2": float(row.carb_split_2 or 0),
                "fat_split_1": float(row.fat_split_1 or 0),
                "fat_split_2": float(row.fat_split_2 or 0),
            }
            for row in page_obj.object_list
        ]
    else:
        qs = ComboMacroErrorLookup.objects.all().order_by("error_code")
        if query:
            qs = qs.filter(error_code__icontains=query)
        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)
        items = [
            {
                "id": row.error_code,
                "protein_error": float(row.protein_error),
                "carbs_error": float(row.carbs_error),
                "fats_error": float(row.fats_error),
            }
            for row in page_obj.object_list
        ]

    return ok(
        {
            "mode": mode,
            "query": query,
            "counts": counts,
            "items": items,
            "pagination": {
                "page": page_obj.number,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
                "total_items": paginator.count,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            },
        }
    )
