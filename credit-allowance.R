library(torch)
library(yaml)

options(scipen = 999)
rnd_error <- 1.0 * (10^(-4))

## Parameters
tree_height <- torch_tensor(11.4, requires_grad = TRUE)
wind_speed <- torch_tensor(64.7,requires_grad = TRUE)
wind_deviation <- torch_tensor(,requires_grad = TRUE)
c17 <- torch_tensor(17, requires_grad = TRUE)
c34 <- torch_tensor(34, requires_grad = TRUE)

## Calculation
calc1 <- tree_height * c17
calc1$retain_grad()

calc2 <- c34 / wind_speed
calc2$retain_grad()

calc3 <- cos(wind_deviation * (pi / 180))
calc3$retain_grad()

calc4 <- calc1 * calc2
calc4$retain_grad()

ans <- calc4 * calc3

## processing
ans$backward()

## results
results <- data.frame(calc = c("calc1", "calc2", "calc3", "calc4", "ans"),
                      val = c(as.numeric(calc1),
                              as.numeric(calc2),
                              as.numeric(calc3),
                              as.numeric(calc4),
                              as.numeric(ans)),
                      grad = c(as.numeric(calc1$grad),
                               as.numeric(calc2$grad),
                               as.numeric(calc3$grad),
                               as.numeric(calc4$grad),
                               1.0),
                      error = rep(rnd_error, 5))

## Ranges
fc <- results$grad %*% results$error
pc <- (abs(results$grad) %*% results$error) * 2

## Answer
ans
fc
pc
