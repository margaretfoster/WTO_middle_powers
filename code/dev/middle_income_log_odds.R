## This script for the Silge implementation of weighted log odds
## based on Monroe et all model

## Save the data from python notebook:
library(tidyverse)
library(dplyr)
library(tidytext)
library(tidylo)
library(ggplot2)
library(forcats) #handling factors
library(ggridges)

wtodata <- readr::read_csv("../data/wtoCTDSpeakerParagraphMto117_varyingInc.csv")
activity_all<-readr::read_csv("activity_by_year.csv")

## First pass, no cleaning:
## group by year, then bind log odds by income level

## First: tokenize text, using tidytext:

word_counts <- wtodata %>%
  unnest_tokens(word, paratext) %>% ## convert paratext to words
  count(year, dynamic_income, word)

## Word log odds:
## Analysis: no clear story line jumping out at me
# The words change a lot by year-- and there's no obvious reason to choose one over the other


log_odds_by_year <- word_counts %>%
  group_by(year) %>%
  bind_log_odds(set = dynamic_income, 
                feature = word,
                n = n) %>%
  ungroup()

log_odds_by_year_LMC = log_odds_by_year %>%
  filter(dynamic_income == "Lower middle income") %>%
  group_by(year) %>%
  slice_max(log_odds_weighted, n = 5) %>%
  arrange(year, desc(log_odds_weighted))

log_odds_by_year_UM = log_odds_by_year %>%
  filter(dynamic_income == "Upper middle income") %>%
  group_by(year) %>%
  slice_max(log_odds_weighted, n = 5) %>%
  arrange(year, desc(log_odds_weighted))

log_odds_by_year_HI = log_odds_by_year %>%
  filter(dynamic_income == "High income") %>%
  group_by(year) %>%
  slice_max(log_odds_weighted, n = 5) %>%
  arrange(year, desc(log_odds_weighted))

log_odds_by_year_EU = log_odds_by_year %>%
  filter(dynamic_income == "Aggregated") %>%
  group_by(year) %>%
  slice_max(log_odds_weighted, n = 5) %>%
  arrange(year, desc(log_odds_weighted))


## Visualization:

log_odds_by_year %>%
  filter(dynamic_income == "Lower middle income") %>%
  group_by(year) %>%
  slice_max(log_odds_weighted, n = 3) %>%
  ggplot(aes(log_odds_weighted, 
             fct_reorder(word, log_odds_weighted), fill = factor(year))) +
  geom_col(show.legend = FALSE) +
  facet_wrap(~ year, scales = "free_y") +
  labs(title = "Top Distinctive Words for LMC Countries by Year",
       x = "Weighted Log-Odds (vs. other groups)", y = NULL)


log_odds_by_year %>%
  filter(dynamic_income == "Upper middle income") %>%
  group_by(year) %>%
  slice_max(log_odds_weighted, n = 8) %>%
  ggplot(aes(log_odds_weighted, 
             fct_reorder(word, log_odds_weighted), fill = factor(year))) +
  geom_col(show.legend = FALSE) +
  facet_wrap(~ year, scales = "free_y") +
  labs(title = "Top Distinctive Words for UMC Countries by Year",
       x = "Weighted Log-Odds (vs. other groups)", y = NULL)


## Compare certain words across time:

log_odds_by_year %>%
  filter(word %in% c("redistributing", "suceptability", "rulemaking")) %>%
  ggplot(aes(dynamic_income, log_odds_weighted, fill = dynamic_income)) +
  geom_col(show.legend = FALSE) +
  facet_grid(word ~ year) +
  labs(title = "Log-Odds by Income Group for Selected Words",
       y = "Weighted Log-Odds", x = "Country Income Group")

## 

log_odds_by_year %>%
  filter(word %in% c("commended", "thanked")) %>%
  ggplot(aes(dynamic_income, 
             log_odds_weighted, 
             fill = dynamic_income)) +
  geom_col(show.legend = FALSE) +
  facet_grid(word ~ year) +
  labs(title = "Log-Odds by Income Group for Selected Words",
       y = "Weighted Log-Odds", x = "Country Income Group")

3##
# Filter to middle-income countries and a few keywords
target_words <- c("development",
                  "redistributing",
                  "technology", "market",
                  "infrastructure")

## NB: This plot has a visualization problem:
log_odds_by_year %>%
  filter(dynamic_income == "Lower middle income", word %in% target_words) %>%
  ggplot(aes(x = year, y = fct_rev(word), 
             height = log_odds_weighted, 
             group = word, fill = word)) +
  geom_ridgeline(stat = "identity", alpha = 0.7, scale = 1.5) +
  labs(
    title = "Time-Varying Distinctiveness of Words for Middle-Income Countries",
    subtitle = "Based on Weighted Log-Odds Compared to Other Income Groups",
    x = "Year", y = "Word (most distinctive at ridge peak)"
  ) +
  theme_minimal() +
  theme(legend.position = "none")


### Country-level view:
## For each country, take their maximum year of activity (?) and then
## run yearly log-odds for the words they use; 
## Pull an interesting word or two, and then look at prevalence of that word
## over time in the corpus; to see if they're introducing and/or pulling forward
## concepts that are then used throughout 

## Qualitative notes:
## 1998 meetings open with India and Egypt discussing technical 
## assistance, and goals for Briefing Sessions;
## Morocco push to expand "special and differential" treatment 
## 1999 topics: subcommittee on Least Developed Countries; 
## "Concerns and problems of small economies"
## 2000: Technical assistance and who is eligible (LDCs/case-by-case)
## Note that the old topic modeling results also help us tell a high-level
## story:
## - "incomeRefs.pdf" shows heatmap of references to TD committe by income
## activity also strongest in the 1998-2005 range, peaking in 2003-2005

## trial 1: Morocco -
## trial 2: Brazil -  peak in 2008, lead up before and gradual decline after
## Trial 3: Korea, main involvement is 1999 then falls out,
## but that might be income upgrading
## Egypt is consistently active
## India's activity increases after 2008, when they become very active
## Djbouti in 2000 and 2002
## Cameroon in 2017
## Venezuela 2004 - big, and unusual for their activity, spike
## Sri Lanka, 2000
## South Africa 2018
## Panama 2011
## Argentina -- two peaks: 2001 and 2017, both with lead-ups
## Barbados: 1998-2006, very little afterwards
## Malaysia: leadup to 2005/2006, then fall off
## Maurtius: 1998-2004, spike in 2000
## Mexico: 1998-2003, dense in 1999/2000

word_counts_country <- wtodata %>%
  unnest_tokens(word, paratext) %>% ## convert paratext to words
  count(year, codes, word) ## ISO3 code to reduce transcription issues

## eg: Panama
log_odds_2011 <- word_counts_country %>%
  group_by(year) %>%
  filter(year == 2011) %>%
  bind_log_odds(set = codes, 
                feature = word,
                n = n) %>%
  ungroup()


log_odds_panama = log_odds_2011 %>%
  filter(codes == "PAN") %>%
  #group_by(year) %>%
  slice_max(log_odds_weighted, n = 15) %>%
  arrange(year, desc(log_odds_weighted))

print(log_odds_panama) ## procedural discussions (discussion; committee; agenda)

## Morocco

max_year <- activity_all %>%
  filter(country == 'Morocco') %>%
  slice_max(speech_count, n = 1, with_ties = FALSE) %>%
  select(year, speech_count)

log_odds_cust <- word_counts_country %>%
  group_by(year) %>%
  filter(year == max_year$year) %>%
  bind_log_odds(set = codes, 
                feature = word,
                n = n) %>%
  ungroup()

log_odds_morocco = log_odds_cust %>%
  filter(codes == "MAR") %>%
  #group_by(year) %>%
  slice_max(log_odds_weighted, n = 15) %>%
  arrange(year, desc(log_odds_weighted))

print(log_odds_morocco) ## procedural discussions (discussion; committee; agenda)
