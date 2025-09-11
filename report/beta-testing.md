
# DID Orderbook DEX – Beta Testing Report

## 1. Overview

This report provides a summary of the external beta testing we performed for our DID orderbook DEX. Our goal was to test the protocol with both individual users and businesses, gather their feedback, and then improve the system based on what we learned. We wanted to confirm that the protocol is usable and effective, while also taking into account real-world requirements such as compliance and risk management for our first iteration. 

---

## 2. Beta Testing Participants

We tested the protocol with four private users and three businesses. The private users represented a range of technical knowledge and familiarity with Cardano and decentralized exchanges. The businesses we spoke with were interested in either using the DEX in their own operations or building services around it. This combination of testers gave us useful feedback from both an everyday user’s perspective and from professional organizations that think more about compliance and operational risks.

---

## 3. What We Tested

The testing covered several areas. We looked at how the protocol itself functions, including the ability to create, cancel, and match orders, as well as how settlement works. We reviewed how the DEX currently handles decentralized identifiers (DIDs). At this stage, we treat DID NFTs as a black box but we still include the DID policy ID in the contracts, so it was important to understand how users and businesses reacted to that approach. We also tested the user experience, especially the ease of connecting wallets, placing orders, and understanding what happens at each stage of the process. Finally, we discussed with the businesses how they view risks and compliance, and whether they believe DID integration helps address these concerns.

---

## 4. Feedback We Collected

The private users confirmed that the Python scripts were able to interact with the contracts as intended. They said that placing and cancelling orders through the scripts worked correctly, and that settlements were processed as expected. However, they noted that using Python commands directly requires technical knowledge, which might be a barrier for less experienced users. Some testers also said that they would like to see more explanatory notes or documentation that describes each step of the workflow, since without an interface the process can feel opaque.

Several of the more experienced testers requested advanced order features that are common in traditional trading systems. One tester specifically asked: "Can we implement stop-loss orders to limit our downside risk? Sometimes we want to automatically sell if the price drops below a certain threshold." Another business tester mentioned that they often need to place large orders and would prefer "minimum fill amounts to avoid getting filled with tiny amounts that create dust in our portfolio." A third tester requested time-weighted average price (TWAP) functionality, saying "We need to execute large orders gradually over time to minimize market impact."

Additionally, the businesses raised important concerns about DID interoperability and compliance control. One institutional tester explained: "We need different levels of DID authentication - some of our trades should only be available to accredited investors, while others might be open to verified business entities." Another compliance-focused tester requested: "Can we restrict certain order types to specific DID categories? For example, large institutional orders should only be fillable by other institutions or accredited investors." A third business user mentioned the need for order modification: "Instead of cancelling and manually recreating orders when we want to change the price, we'd prefer a single atomic operation that modifies the existing order. This reduces the risk of being left without an active order during market volatility."

The businesses provided feedback that was more focused on compliance and long-term usage. They welcomed the fact that DIDs are already part of the contract design and saw this as an important foundation for trust. At the same time, they raised concerns about interoperability and asked what would happen if different DID providers were used. They also highlighted the importance of having different DID types to enable more fine-grained compliance control and maybe even a business type (like accredidated investor) included in the actual protocol. 

---

## 5. Changes We Made Based on Feedback

Based on this round of testing, we focused on strengthening the code and the testing environment. The most important change was the addition of a comprehensive test suite in the smart contract repository. This allows us to automatically check that the contracts behave as expected and gives external developers a stronger foundation for their own testing. We also expanded the Python scripts with clearer logging and comments so that it is easier for new testers to understand what is happening when they run commands.

In response to the requests for advanced trading features, we implemented support for advanced order types directly in the smart contracts. The orderbook now supports stop-loss orders that automatically trigger when market conditions are met, minimum fill amounts to prevent dust transactions, and the foundation for time-weighted average price (TWAP) orders. These features are integrated into both the on-chain validation logic and the off-chain Python scripts. Users can now place orders with `--stop-loss-price`, `--min-fill-amount`, and `--twap-interval` parameters, and the order matching system automatically detects and handles these advanced order types appropriately.

To address the DID interoperability and compliance concerns, we extended the system to support multiple DID provider types and authentication levels. The smart contracts now recognize different categories of DIDs including basic verified users, accredited investors, and business entities. Order creators can specify DID requirements for their counterparties using flags like `--require-accredited-investor` or `--require-business-entity`. The on-chain validation automatically checks that order fillers meet the specified DID requirements, enabling fine-grained compliance control while maintaining interoperability across different DID providers.

We also implemented atomic order modification functionality through a new `modify_order.py` script. This addresses the risk concern raised by institutional users by allowing them to change order parameters (price, amounts, DID requirements) in a single transaction showing that they can change limit amounts without having to cancel and replace the order in seperate transactions. This ensures users are never left without an active order during modification, which is crucial during volatile market conditions. 

---

## 6. What We Learned

The beta test showed us that the smart contracts are functioning correctly, but that working directly with Python scripts is not accessible for everyone. We learned that providing clear documentation and test tools is just as important as building the contracts themselves at this stage. We also learned that businesses see DID integration as a valuable feature, but they want to know how it will handle multiple providers and interoperability in the future. Adding the test suite to the repository was an important step, because it demonstrates both to ourselves and to external partners that the contracts can be trusted.

The request for advanced order types taught us that even at this early stage, users expect sophisticated trading features that are comparable to traditional exchanges. Implementing stop-loss, minimum fill, and TWAP orders required careful consideration of how to maintain the security and simplicity of the smart contracts while adding complex logic. We learned that modular design is crucial - by creating separate validation functions and redeemer types, we were able to extend functionality without compromising the existing system. This experience also highlighted the importance of having both basic and advanced modes, allowing simple users to continue with straightforward orders while giving sophisticated traders the tools they need.

The DID interoperability requirements revealed the complexity of compliance in decentralized systems. We learned that a one-size-fits-all approach to DID validation would not work for diverse business needs. By implementing a flexible DID type system that supports multiple providers and authentication levels, we were able to address regulatory requirements while maintaining the decentralized nature of the system. The challenge was balancing security (ensuring DID authenticity) with usability (not making the system too restrictive). We also discovered that institutional users have very specific risk management needs, such as atomic order modification, which required us to think creatively about transaction composition to solve real-world trading concerns.

