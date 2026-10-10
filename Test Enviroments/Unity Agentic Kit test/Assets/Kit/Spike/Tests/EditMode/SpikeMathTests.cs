using NUnit.Framework;

namespace Kit.Spike.Tests
{
    public class SpikeMathTests
    {
        [Test]
        public void Lerp01_Midpoint_ReturnsAverage()
        {
            Assert.AreEqual(5f, SpikeMath.Lerp01(0f, 10f, 0.5f), 1e-5f);
        }

        [Test]
        public void Lerp01_TBelowZero_ClampsToA()
        {
            Assert.AreEqual(2f, SpikeMath.Lerp01(2f, 8f, -3f), 1e-5f);
        }

        [Test]
        public void Lerp01_TAboveOne_ClampsToB()
        {
            Assert.AreEqual(8f, SpikeMath.Lerp01(2f, 8f, 4f), 1e-5f);
        }
    }
}
