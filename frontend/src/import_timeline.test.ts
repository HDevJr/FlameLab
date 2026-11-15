import { describe, expect, it } from "vitest";
import { timeShares } from "./ImportTimeline";

describe("linha do tempo da importação", () => {
  it("fatia o tempo total entre as etapas usando só durações reais", () => {
    const s = timeShares([100, 300, null, 600]);
    expect(s.map((x) => Math.round(x * 100))).toEqual([10, 30, 0, 60]);
  });
  it("sem tempo registrado não inventa porcentagem", () => expect(timeShares([null, null, 0])).toEqual([0, 0, 0]));
});
