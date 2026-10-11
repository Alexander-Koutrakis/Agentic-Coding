namespace Kit.Spike
{
    public static class SpikeMath
    {
        public static float Lerp01(float a, float b, float t)
        {
            if (t < 0f) t = 0f;
            else if (t > 1f) t = 1f;
            return a + (b - a) * t;
        }
    }
}
