package com.legacyinsure.policies;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.HashMap;
import java.util.Map;

/**
 * Represents a single insurance policy with premium calculation logic.
 * In production since 2007. The premium formula was last audited in 2019.
 */
public class InsurancePolicy {

    public enum PolicyType {
        AUTO, HOME, LIFE, HEALTH
    }

    public enum RiskLevel {
        LOW, MEDIUM, HIGH
    }

    private static final Map<PolicyType, Double> BASE_PREMIUMS = new HashMap<>();
    static {
        BASE_PREMIUMS.put(PolicyType.AUTO, 1200.0);
        BASE_PREMIUMS.put(PolicyType.HOME, 800.0);
        BASE_PREMIUMS.put(PolicyType.LIFE, 500.0);
        BASE_PREMIUMS.put(PolicyType.HEALTH, 1500.0);
    }

    private static final Map<RiskLevel, Double> RISK_MULTIPLIERS = new HashMap<>();
    static {
        RISK_MULTIPLIERS.put(RiskLevel.LOW, 1.0);
        RISK_MULTIPLIERS.put(RiskLevel.MEDIUM, 1.5);
        RISK_MULTIPLIERS.put(RiskLevel.HIGH, 2.5);
    }

    private String policyId;
    private String holderName;
    private PolicyType type;
    private RiskLevel riskLevel;
    private LocalDate startDate;
    private LocalDate endDate;
    private int claimsCount;
    private boolean active;

    public InsurancePolicy(String policyId, String holderName, PolicyType type,
                           RiskLevel riskLevel, LocalDate startDate, int termYears) {
        if (policyId == null || policyId.trim().isEmpty()) {
            throw new IllegalArgumentException("Policy ID is required");
        }
        if (holderName == null || holderName.trim().isEmpty()) {
            throw new IllegalArgumentException("Holder name is required");
        }
        if (termYears < 1 || termYears > 30) {
            throw new IllegalArgumentException("Term must be between 1 and 30 years");
        }
        this.policyId = policyId.trim();
        this.holderName = holderName.trim();
        this.type = type;
        this.riskLevel = riskLevel;
        this.startDate = startDate;
        this.endDate = startDate.plusYears(termYears);
        this.claimsCount = 0;
        this.active = true;
    }

    public String getPolicyId() { return policyId; }
    public String getHolderName() { return holderName; }
    public PolicyType getType() { return type; }
    public RiskLevel getRiskLevel() { return riskLevel; }
    public LocalDate getStartDate() { return startDate; }
    public LocalDate getEndDate() { return endDate; }
    public int getClaimsCount() { return claimsCount; }
    public boolean isActive() { return active; }

    /**
     * Calculate annual premium based on policy type, risk, claims history,
     * and policy age (loyalty discount).
     */
    public double calculateAnnualPremium() {
        double base = BASE_PREMIUMS.getOrDefault(type, 1000.0);
        double riskMult = RISK_MULTIPLIERS.getOrDefault(riskLevel, 1.0);

        double premium = base * riskMult;

        // Claims surcharge: +15% per claim, capped at +75%
        double claimsSurcharge = Math.min(claimsCount * 0.15, 0.75);
        premium *= (1.0 + claimsSurcharge);

        // Loyalty discount: -2% per full year of policy age, capped at -20%
        long yearsHeld = ChronoUnit.YEARS.between(startDate, LocalDate.now());
        double loyaltyDiscount = Math.min(yearsHeld * 0.02, 0.20);
        premium *= (1.0 - loyaltyDiscount);

        return Math.round(premium * 100.0) / 100.0;
    }

    /**
     * File a claim. Increases claims count if policy is active
     * and not expired.
     */
    public boolean fileClaim() {
        if (!active) {
            return false;
        }
        if (LocalDate.now().isAfter(endDate)) {
            active = false;
            return false;
        }
        claimsCount++;
        return true;
    }

    /**
     * Cancel the policy. Returns a prorated refund fraction
     * (0.0 to 1.0) based on remaining term.
     */
    public double cancel() {
        if (!active) {
            return 0.0;
        }
        active = false;
        long totalDays = ChronoUnit.DAYS.between(startDate, endDate);
        long elapsed = ChronoUnit.DAYS.between(startDate, LocalDate.now());
        if (elapsed >= totalDays) {
            return 0.0;
        }
        double remaining = (double)(totalDays - elapsed) / totalDays;
        return Math.round(remaining * 100.0) / 100.0;
    }

    public String getSummary() {
        return String.format("Policy[%s] %s | %s/%s | Active: %s | Claims: %d",
                policyId, holderName, type, riskLevel,
                active ? "YES" : "NO", claimsCount);
    }
}
