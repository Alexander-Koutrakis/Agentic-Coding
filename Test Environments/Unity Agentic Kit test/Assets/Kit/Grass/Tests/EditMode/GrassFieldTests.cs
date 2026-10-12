using System;
using NUnit.Framework;
using UnityEngine;

namespace Kit.Grass.Tests
{
    public class GrassFieldTests
    {
        static GrassFieldCreateInfo Info(int seed = 1, int count = 100) => new GrassFieldCreateInfo
        {
            seed = seed,
            bladeCount = count,
            patchSize = new Vector2(10f, 6f),
            patchCenter = new Vector3(5f, 2f, -3f),
            minScale = 0.5f,
            maxScale = 1.5f,
        };

        [Test]
        public void Create_SameSeedAndCount_GivesIdenticalMatrices()
        {
            var a = GrassField.Create(Info()).Matrices;
            var b = GrassField.Create(Info()).Matrices;
            Assert.AreEqual(a, b);
        }

        [Test]
        public void Create_DifferentSeed_GivesDifferentMatrices()
        {
            var a = GrassField.Create(Info(1)).Matrices;
            var b = GrassField.Create(Info(2)).Matrices;
            Assert.AreNotEqual(a, b);
        }

        [Test]
        public void Create_CountN_MatricesLengthIsN()
        {
            var field = GrassField.Create(Info(1, 37));
            Assert.AreEqual(37, field.Matrices.Length);
            Assert.AreEqual(37, field.BladeCount);
        }

        [Test]
        public void Create_ZeroBlades_GivesEmptyArray()
        {
            Assert.AreEqual(0, GrassField.Create(Info(1, 0)).Matrices.Length);
        }

        [Test]
        public void Create_Blades_StayInsidePatchAtCenterHeight()
        {
            var info = Info(7, 500);
            foreach (var m in GrassField.Create(info).Matrices)
            {
                Vector3 p = m.GetColumn(3);
                Assert.That(p.x, Is.InRange(info.patchCenter.x - 5f, info.patchCenter.x + 5f));
                Assert.That(p.z, Is.InRange(info.patchCenter.z - 3f, info.patchCenter.z + 3f));
                Assert.AreEqual(info.patchCenter.y, p.y);
            }
        }

        [Test]
        public void Create_Blades_ScaleInsideRange()
        {
            foreach (var m in GrassField.Create(Info(3, 500)).Matrices)
                Assert.That(m.lossyScale.x, Is.InRange(0.5f - 1e-4f, 1.5f + 1e-4f));
        }

        [Test]
        public void Create_FewerBlades_IsPrefixOfMore()
        {
            var small = GrassField.Create(Info(5, 10)).Matrices;
            var large = GrassField.Create(Info(5, 20)).Matrices;
            for (int i = 0; i < small.Length; i++)
                Assert.AreEqual(small[i], large[i]);
        }

        [Test]
        public void Create_BadInfo_Throws()
        {
            var negative = Info(); negative.bladeCount = -1;
            var flat = Info(); flat.patchSize = new Vector2(0f, 5f);
            var zeroMin = Info(); zeroMin.minScale = 0f;
            var inverted = Info(); inverted.minScale = 2f; inverted.maxScale = 1f;
            Assert.Throws<ArgumentException>(() => GrassField.Create(negative));
            Assert.Throws<ArgumentException>(() => GrassField.Create(flat));
            Assert.Throws<ArgumentException>(() => GrassField.Create(zeroMin));
            Assert.Throws<ArgumentException>(() => GrassField.Create(inverted));
        }
    }
}
