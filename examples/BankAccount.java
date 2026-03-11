package com.legacybank.accounts;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Core bank account used across the retail banking platform since 2004.
 * Handles deposits, withdrawals, transfers, and interest accrual.
 * WARNING: Do not modify without approval from the Risk team.
 */
public class BankAccount {

    private String accountId;
    private String ownerName;
    private double balance;
    private double interestRate;
    private boolean frozen;
    private List<String> transactionHistory;

    public BankAccount(String accountId, String ownerName, double initialBalance, double interestRate) {
        if (accountId == null || accountId.trim().isEmpty()) {
            throw new IllegalArgumentException("Account ID cannot be null or empty");
        }
        if (initialBalance < 0) {
            throw new IllegalArgumentException("Initial balance cannot be negative");
        }
        if (interestRate < 0 || interestRate > 1.0) {
            throw new IllegalArgumentException("Interest rate must be between 0 and 1");
        }
        this.accountId = accountId.trim();
        this.ownerName = ownerName != null ? ownerName.trim() : "Unknown";
        this.balance = initialBalance;
        this.interestRate = interestRate;
        this.frozen = false;
        this.transactionHistory = new ArrayList<>();
        this.transactionHistory.add("OPEN:" + initialBalance);
    }

    public String getAccountId() {
        return accountId;
    }

    public String getOwnerName() {
        return ownerName;
    }

    public double getBalance() {
        return balance;
    }

    public boolean isFrozen() {
        return frozen;
    }

    public List<String> getTransactionHistory() {
        return Collections.unmodifiableList(transactionHistory);
    }

    public void deposit(double amount) {
        if (frozen) {
            throw new IllegalStateException("Cannot deposit to a frozen account");
        }
        if (amount <= 0) {
            throw new IllegalArgumentException("Deposit amount must be positive");
        }
        balance += amount;
        transactionHistory.add("DEP:" + amount);
    }

    public void withdraw(double amount) {
        if (frozen) {
            throw new IllegalStateException("Cannot withdraw from a frozen account");
        }
        if (amount <= 0) {
            throw new IllegalArgumentException("Withdrawal amount must be positive");
        }
        if (amount > balance) {
            throw new IllegalArgumentException("Insufficient funds");
        }
        balance -= amount;
        transactionHistory.add("WDR:" + amount);
    }

    /**
     * Transfer funds to another account. Both accounts must not be frozen.
     * This is NOT atomic — if the deposit into the target fails, the
     * withdrawal from this account is NOT rolled back. (Known tech-debt.)
     */
    public void transfer(BankAccount target, double amount) {
        if (target == null) {
            throw new IllegalArgumentException("Target account cannot be null");
        }
        if (target.getAccountId().equals(this.accountId)) {
            throw new IllegalArgumentException("Cannot transfer to the same account");
        }
        this.withdraw(amount);
        target.deposit(amount);
        transactionHistory.add("TRF:" + amount + ":" + target.getAccountId());
    }

    /**
     * Apply annual interest. Only applies if balance is positive and
     * account is not frozen.
     */
    public double applyInterest() {
        if (frozen) {
            return 0.0;
        }
        if (balance <= 0) {
            return 0.0;
        }
        double interest = Math.round(balance * interestRate * 100.0) / 100.0;
        balance += interest;
        transactionHistory.add("INT:" + interest);
        return interest;
    }

    public void freeze() {
        this.frozen = true;
        transactionHistory.add("FREEZE");
    }

    public void unfreeze() {
        this.frozen = false;
        transactionHistory.add("UNFREEZE");
    }

    /**
     * Produces a summary string used by downstream reporting.
     */
    public String getSummary() {
        return String.format("[%s] %s | Balance: %.2f | Frozen: %s | Txns: %d",
                accountId, ownerName, balance, frozen ? "YES" : "NO",
                transactionHistory.size());
    }
}
