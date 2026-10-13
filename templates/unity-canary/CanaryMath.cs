namespace Kit.Canary
{
    // Known-good code for the kit's gate: it must always compile, pass format and code rules, and its tests must pass.
    public static class CanaryMath
    {
        public static float Lerp01(float a, float b, float t)
        {
            if (t < 0f) t = 0f;
            else if (t > 1f) t = 1f;
            return a + (b - a) * t;
        }
    }
}
