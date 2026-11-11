import { test, expect } from '@playwright/test';

test('all authored shots get three bounded, non-repeating shared variants', async ({ page }) => {
  await page.goto('/');
  const result = await page.evaluate(async () => {
    const { getAllShotAnimations } = await import('/src/data/shotAnimations.ts');
    const { createShotVariant, getShotVariationBounds, nextShotVariant, varyShotAnimation, varyReferenceShot } =
      await import('/src/data/shotVariants.ts');
    const references = (await import('/src/data/reference_shots.json')).default as Record<string, any>;
    const failures: string[] = [];
    const animations = getAllShotAnimations();

    for (const animation of animations) {
      const bounds = getShotVariationBounds(animation.name);
      const reference = references[animation.name];
      const signatures = new Set<string>();
      for (const id of [0, 1, 2]) {
        const variant = createShotVariant(id, animation.name);
        if (Math.abs(variant.strideScale - 1) > bounds.stride + 1e-9) failures.push(`${animation.name}: stride bound`);
        if (Math.abs(variant.leanOffset) > bounds.lean + 1e-9) failures.push(`${animation.name}: lean bound`);
        if (Math.abs(variant.followThroughScale - 1) > bounds.finish + 1e-9) failures.push(`${animation.name}: finish bound`);
        const threeD = varyShotAnimation(animation, variant);
        const twoD = reference ? varyReferenceShot(reference, variant) : null;
        if (twoD && Math.abs(threeD.phases.downswing.durationWeight - animation.phases.downswing.durationWeight / variant.tempo) > 1e-9) {
          failures.push(`${animation.name}: 2D/3D tempo mismatch`);
        }
        signatures.add(`${variant.tempo}:${variant.strideScale}:${variant.leanOffset}:${variant.followThroughScale}`);
      }
      if (signatures.size !== 3) failures.push(`${animation.name}: fewer than three distinct profiles`);

      let previous = -1;
      for (let play = 0; play < 12; play += 1) {
        const selected = nextShotVariant(previous, animation.name);
        if (selected.id === previous) failures.push(`${animation.name}: immediate variant repeat`);
        previous = selected.id;
      }
    }
    return { shotCount: animations.length, failures };
  });

  expect(result.shotCount).toBe(25);
  expect(result.failures).toEqual([]);
});
