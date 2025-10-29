"""
TEST SCRIPT - Verify Timing Logic
---------------------------------
Run this in Django shell (or as a standalone script)
to verify which parameter groups should be available
for a given checklist based on elapsed time.
"""

from main.models import ChecklistBase, ParameterGroupConfig
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ObjectDoesNotExist

# === CONFIGURATION ===
# Change this ID to the checklist you want to test
checklist_id = 118

print("=" * 60)
print("TIMING LOGIC TEST")
print("=" * 60)

# === GET CHECKLIST ===
try:
    checklist = ChecklistBase.objects.get(id=checklist_id)
except ObjectDoesNotExist:
    print(f"❌ Checklist with ID {checklist_id} not found.")
    quit()

# === CHECKLIST INFO ===
print(f"\nChecklist ID: {checklist.id}")
print(f"Model: {checklist.selected_model}")
print(f"Created at: {checklist.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

# === TIME ELAPSED ===
time_elapsed = timezone.now() - checklist.created_at
minutes_elapsed = time_elapsed.total_seconds() / 60

print(f"\nTime elapsed: {minutes_elapsed:.1f} minutes")
print(f"Current time: {timezone.now().strftime('%H:%M:%S')}")

# === FETCH PARAMETER GROUP CONFIGS ===
configs = ParameterGroupConfig.objects.filter(
    model_name=checklist.selected_model,
    is_active=True
).order_by('display_order')

print(f"\n{'Parameter':<30} {'Frequency':<12} {'Status':<30}")
print("-" * 72)

available_groups = []

for config in configs:
    freq = config.frequency_minutes
    display_name = getattr(config, "get_parameter_group_display", lambda: config.parameter_group)()

    if minutes_elapsed >= freq:
        status = f"✓ AVAILABLE (after {freq} min)"
        available_groups.append(display_name)
    else:
        remaining = freq - minutes_elapsed
        status = f"⏰ Pending ({remaining:.0f} min left)"
    
    print(f"{display_name:<30} {freq:>3} min      {status}")

# === SUMMARY ===
print("\n" + "=" * 60)
print("EXPECTED BEHAVIOR:")
print("=" * 60)

available_count = len(available_groups)
print(f"\nCurrently available: {available_count} parameter group(s)")

if available_count == 0:
    print("→ No forms should be visible yet.")
elif available_count == 1:
    print("→ Should see: UV Vacuum Test form")
elif available_count == 2:
    print("→ Should see: UV Vacuum Test + UV Flow Value forms")
elif available_count == 3:
    print("→ Should see: UV Vacuum + UV Flow + Umbrella Valve forms")
elif available_count >= 4:
    print(f"→ Should see {available_count} forms at once!")

if available_groups:
    print("\n✅ Available now:", ", ".join(available_groups))
else:
    print("\n⏳ No parameter groups available yet.")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
