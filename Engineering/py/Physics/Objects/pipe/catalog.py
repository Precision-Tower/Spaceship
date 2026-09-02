INCH_TO_M = 0.0254

PVC_SCH40 = {
    1.0: {"od_in": 1.315, "id_in": 1.049},
    1.5: {"od_in": 1.900, "id_in": 1.610},
    2.0: {"od_in": 2.375, "id_in": 2.067},
}


def pvc_pipe_dimensions(
    *,
    nominal_size_in: float,
    schedule: str = "SCH40",
) -> dict:
    if schedule != "SCH40":
        raise ValueError(f"Unsupported PVC schedule: {schedule}")

    if nominal_size_in not in PVC_SCH40:
        raise ValueError(f"Unsupported PVC nominal_size_in: {nominal_size_in}")

    item = PVC_SCH40[nominal_size_in]

    return {
        "nominal_size_in": nominal_size_in,
        "schedule": schedule,
        "outer_diameter_m": item["od_in"] * INCH_TO_M,
        "inner_diameter_m": item["id_in"] * INCH_TO_M,
        "outer_radius_m": item["od_in"] * INCH_TO_M / 2.0,
        "inner_radius_m": item["id_in"] * INCH_TO_M / 2.0,
        "wall_thickness_m": (item["od_in"] - item["id_in"]) * INCH_TO_M / 2.0,
    }