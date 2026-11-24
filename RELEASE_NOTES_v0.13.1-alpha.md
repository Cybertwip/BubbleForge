# BubbleForge v0.13.1-alpha — Bridge derating repair

- Corrected the ambiguous `derating failure` backend exception. The 60 V silicon bridge fails the existing 80%-of-rating nominal bus screen at 48 V input; 48 V remains supported using the 93 V-rated GaN stage.
- Selecting the Si bridge from the 48 V reference point automatically moves to a 45 V input, 39.6 V output screening case. Raising the input back to 48 V while on Si switches to the GaN bridge. Both adjustments are explicitly explained in the UI; no invalid setting is silently treated as valid.
- Matched the output-slider ceiling to the Python model's duty margin and fixed the browser slider-max clamping order.
- Displayed real API parameter-validation failures as such, rather than incorrectly telling users to start the already-running server. Stale energy values and plots are cleared whenever a request fails.
- Kept the original source-paid pulse, acoustic pickup, battery ledger and the two single-page PDFs. No values were altered to meet an efficiency target.
- Verification: Python regression suite, HTTP API for valid and invalid configurations, and offline DOM interaction (full browser network navigation restricted by environment). All results remain nominal modeling rather than bench measurements.
