using NUnit.Framework;

namespace Kit.Canary.Tests
{
    public class CanaryMathTests
    {
        [Test]
        public void Lerp01_Midpoint_ReturnsAverage()
        {
            Assert.AreEqual(5f, CanaryMath.Lerp01(0f, 10f, 0.5f), 1e-5f);
        }

        [Test]
        public void Lerp01_TBelowZero_ClampsToA()
        {
            Assert.AreEqual(2f, CanaryMath.Lerp01(2f, 8f, -3f), 1e-5f);
        }

        [Test]
        public void Lerp01_TAboveOne_ClampsToB()
        {
            Assert.AreEqual(8f, CanaryMath.Lerp01(2f, 8f, 4f), 1e-5f);
        }
    }
}
