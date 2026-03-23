# Pricing theory for real estate 101

From an optimization perspective, pricing a property is not a static calculation but a stochastic control problem. You are essentially trying to maximize the **Expected Net Proceeds** while accounting for the inverse relationship between price and the probability of a timely sale.

In a formal ML framework, the objective function to maximize the Net Proceeds $J(P)$ can be expressed as:

$$J(P) = P \cdot \mathbb{P}(\text{Sale} | P, \Delta t) - \int_{0}^{T(P)} C_h(t) dt$$

### Components of the Equation

1.  **The Hedonic Base ($P$):**
    This is your list price. It is usually derived from a base regressor (linear regression, or ML like an XGBoost or LightGBM model) trained on historical sold data:
    $$P_{base} = \beta_0 + \sum_{i=1}^{n} \beta_i X_i + \epsilon$$
    where $X_i$ represents features like square footage, location embeddings, and condition scores.

2.  **Probability of Sale $\mathbb{P}(\text{Sale} | P, \Delta t)$:**
    This is the "Liquidity Function." The probability of sale decreases as $P$ deviates from the fair market value ($P_{fmv}$). This is often modeled using a **Logistic Decay** or **Survival Analysis** (Cox Proportional Hazards):
    $$\mathbb{P}(\text{Sale} | P, \Delta t) = \frac{1}{1 + e^{k(P - P_{fmv})}}$$
    * If $P \gg P_{fmv}$, the probability of sale approaches zero.
    * The parameter $k$ represents the "Market Sensitivity" (volatility).

3.  **The Holding Cost Function $C_h(t)$:**
    This represents the "burn rate" of the property. For a FSBO seller, this includes:
    * **Direct Costs:** Mortgage interest, taxes, insurance, and maintenance.
    * **Opportunity Cost:** The capital tied up in the home that isn't being invested elsewhere.
    * **Staleness Discount:** A penalty where the perceived value of a listing drops the longer it remains active (Days On Market or $DOM$). 

---

### The Optimization Strategy: The "Sweet Spot"

To find the optimal price $P^*$, you take the derivative of the objective function and set it to zero:

$$\frac{dJ}{dP} = 0$$

This identifies the point where the marginal increase in revenue from a higher price is exactly offset by the marginal increase in holding costs and the decreased probability of closing the deal.

| Variable | Impact on $P^*$ | Reason |
| :--- | :--- | :--- |
| **Inventory ($\uparrow$)** | Decrease | Higher competition lowers $\mathbb{P}(\text{Sale})$ at any given price. |
| **Interest Rates ($\uparrow$)** | Decrease | Increases the buyer's monthly cost, shifting $P_{fmv}$ downward. |
| **Seller Urgency ($\uparrow$)** | Decrease | Increases the weight of $C_h(t)$, favoring a faster exit. |

---

### Dynamic Pricing (The MDP Approach)
You can treat pricing as a **Markov Decision Process (MDP)**. 

In this state-space, the "Action" is the price adjustment at interval $t$. The reward function is the final sale price minus the cumulative holding costs.
* **State ($S$):** Current price, $DOM$, click-through rate, and current inventory.
* **Action ($A$):** $P_{new} = P_{old} + \Delta P$.
* **Transition ($T$):** The probability of moving to a "Sold" state or remaining "Active" with an increased $DOM$.

### Liquidity Decay Curve
The **Liquidity Decay Curve** is a mathematical model that maps the inverse relationship between an asking price and the probability of a transaction occurring within a specific timeframe.  Essentially, it visualizes how "liquid" a property is at various price points. As the price moves further above the Fair Market Value ($P_{fmv}$), the pool of eligible buyers does not just shrink—it evaporates at an accelerating rate.

#### 1. The Mathematical Structure
The curve is most commonly represented as a **Sigmoid (Logistic) Function**. This is because the probability of a sale is relatively stable near or below market value, but it hits a "tipping point" where even small price increases lead to a total loss of liquidity.

A common representation for your optimization model would be:

$$\mathbb{P}(\text{Sale} | P) = \frac{1}{1 + e^{k(P - P_{fmv})}}$$

* **$P$:** The Asking Price.
* **$P_{fmv}$:** The Fair Market Value (the "inflection point" where the probability of sale is 50%).
* **$k$:** The **Market Sensitivity Coefficient**. 
    * In a "Hot Market," $k$ is low (the curve is flatter), meaning buyers are less sensitive to overpricing.
    * In a "Cold Market," $k$ is high (the curve is steep), meaning even a 2–3% overage kills interest.

---

#### 2. The Three Zones of the Curve
When building an algorithm, you can segment the curve into three distinct behavioral zones:

| Zone | Price Range | Liquidity Signal |
| :--- | :--- | :--- |
| **The Auction Zone** | $P < P_{fmv}$ | High probability of multiple offers. Liquidity is essentially 100%. |
| **The Equilibrium Zone** | $P \approx P_{fmv}$ | Probability of sale is 40–60%. Sale timing depends on marketing and specific buyer fit. |
| **The Dead Zone** | $P > 1.1 \cdot P_{fmv}$ | Probability of sale drops toward zero. The property becomes a "stale" listing. |

---

#### 3. The "Staleness" Factor (Time-Based Decay)
Liquidity decay isn't just about price; it’s also a function of **Days on Market (DOM)**. This creates a 3D surface where liquidity decays over both price and time.

* **Initial Liquidity:** In the first 7–14 days, a listing has maximum visibility.
* **Search Filter Marginalization:** After 30 days, most automated "New Listing" alerts for buyers have already fired. The property is now only being seen by "new-to-market" buyers, which is a much smaller pool.
* **Stigma Discount:** If a property remains on the curve too long without a sale, buyers begin to "price in" a hidden defect (e.g., "What is wrong with this house that no one else bought it?"). This shifts the entire curve downward.


---

#### 4. Application in Price Optimization
The goal is to find the **Global Maximum** of the Expected Revenue.

If you price too low, you lose money on the sale price ($P$). If you price too high, you lose money to the **Holding Cost** ($C_h$) and the risk that $\mathbb{P}(\text{Sale})$ becomes so low that the property never sells.

$$P^* = \arg\max_P \left[P \cdot \mathbb{P}(\text{Sale} | P) - \int_{0}^{T(P)} C_h(t) dt\right]$$

By observing market signals (such as digital engagement metrics, showing volume, and competitive activity), you are essentially trying to estimate the value of $k$ (the slope of the decay) in real-time to determine if a price cut is necessary to move the listing back into the **Equilibrium Zone**.


